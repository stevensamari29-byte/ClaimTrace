"""Read-only SQL using the existing externally stored Zetaris configuration.

No datasets are created by this module. Config paths/credentials stay server-side.
"""
import json
import os
import re
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .models import Company, Evidence
from .sources import SourceError


def configuration():
    config = {}
    path = os.getenv('ZETARIS_CONFIG_PATH')
    if path:
        for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                if key.strip().startswith('ZETARIS_'):
                    config[key.strip()] = value.strip().strip('"').strip("'")
    config.update({k: v for k, v in os.environ.items() if k.startswith('ZETARIS_')})
    return config


def query(sql, limit=25):
    if not re.match(r'^\s*(SELECT\b|SHOW\s+LIGHTNING\s+(DATABASES|TABLES)\b|DESCRIBE\b)', sql, re.I) or ';' in sql:
        raise SourceError('Only a single bounded read-only SQL statement is permitted.')
    try:
        config = configuration()
        base = config.get('ZETARIS_BASE_URL', '').rstrip('/')
        parsed = urlsplit(base)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise SourceError('Configure the existing HTTPS Zetaris endpoint externally.')
        token, org = config['ZETARIS_API_KEY'], config['ZETARIS_ORG_ID']
        if not org.isdigit():
            raise SourceError('Zetaris organization configuration is invalid.')
        headers = {'Authorization': 'Bearer ' + token, 'X-Org-ID': org, 'X-Request-ID': str(uuid.uuid4())}
        with httpx.Client(timeout=25, follow_redirects=False) as client:
            with client.stream('POST', base + '/api/proxy/sql-editor/sqls/run-query', headers=headers,
                               json={'sql': sql, 'limit': min(max(1, limit), 100)}) as response:
                response.raise_for_status()
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 1_000_000:
                        raise SourceError('Zetaris response exceeded the 1 MB bound.')
            return json.loads(raw)
    except SourceError:
        raise
    except (KeyError, OSError, httpx.HTTPError, ValueError):
        raise SourceError('Zetaris unavailable or not configured; financial dataset approval/import may still be required.') from None


def result_rows(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        headers, data = payload.get('headers'), payload.get('data')
        if isinstance(headers, list) and all(isinstance(h, str) for h in headers) and isinstance(data, list):
            if all(isinstance(row, list) and len(row) == len(headers) for row in data):
                return [dict(zip(headers, row)) for row in data]
        for key in ('data', 'rows', 'result', 'results'):
            value = payload.get(key)
            if isinstance(value, list) and (not value or isinstance(value[0], dict)):
                return value
            if isinstance(value, dict):
                found = result_rows(value)
                if found:
                    return found
    raise SourceError('Zetaris returned an unsupported result shape; no financial evidence was inferred.')


def zetaris_evidence(request):
    table = os.getenv('CLAIMTRACE_ZETARIS_TABLE', '')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*){0,2}', table):
        raise SourceError('Zetaris financial dataset is not configured. Cloud dataset creation/import requires owner approval.')
    cik = request.company.cik.zfill(10)
    sql = (f"SELECT evidence_id, cik, company_name, ticker, fiscal_year, fiscal_period, reporting_period_end, document, source_url, published_at, period_start, period_end, unit, value, concept, locator, source_sha256 "
           f"FROM {table} WHERE cik = '{cik}' AND fiscal_year = {request.fiscal_year} AND fiscal_period = '{request.period}' "
           f"AND published_at <= '{request.as_of.isoformat()}' LIMIT 25")
    rows = result_rows(query(sql))
    evidence = []
    canonical = None
    for row in rows:
        try:
            if (str(row['cik']).zfill(10) != cik or int(row['fiscal_year']) != request.fiscal_year
                    or row['fiscal_period'] != request.period or row['reporting_period_end'] != row['period_end']):
                raise ValueError('Reporting metadata mismatch')
            identity = Company(name=row['company_name'],ticker=row['ticker'],cik=cik)
            if canonical is not None and identity != canonical:
                raise ValueError('Conflicting source identity')
            canonical = identity
            evidence.append(Evidence(id=row['evidence_id'], document=row['document'], url=row['source_url'],
                published_at=row['published_at'], period_start=row['period_start'], period_end=row['period_end'],
                unit=row['unit'], value=row['value'], concept=row['concept'], locator=row['locator'],
                source_mode='live_zetaris', source_sha256=row.get('source_sha256')))
        except (KeyError, ValueError, TypeError):
            raise SourceError('Zetaris financial evidence failed schema validation.') from None
    if any(e.published_at > request.as_of or e.period_end > request.as_of for e in evidence):
        raise SourceError('Zetaris returned evidence after the requested as-of date.')
    for e in evidence:
        days = (e.period_end - e.period_start).days + 1
        valid = 330 <= days <= 380 if request.period == 'FY' else 70 <= days <= 105
        if not valid:
            raise SourceError('Zetaris evidence does not match the supported reporting period.')
    if canonical:
        request.company = canonical
    return evidence
