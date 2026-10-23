"""Bounded SEC retrieval. Snapshots are authentic cached evidence, never live proof."""
import hashlib
import json
import os
import re
import threading
import time
from datetime import date
from pathlib import Path

import httpx

from .models import Company, Evidence, InvestigationRequest

DATA = Path(__file__).parent / 'data' / 'isrg-q2-2026-evidence.json'
LOCAL_CONFIG_PATH = Path(__file__).parents[1] / '.env.local'
CONCEPTS = ('RevenueFromContractWithCustomerExcludingAssessedTax', 'Revenues',
            'NetIncomeLoss', 'EarningsPerShareDiluted', 'OperatingIncomeLoss', 'GrossProfit')
_lock = threading.Lock()
_last = 0.0


class SourceError(RuntimeError):
    pass


def sec_user_agent():
    """Construct identity from the approved organization and a private bare email."""
    local_value = ''
    if 'SEC_CONTACT_EMAIL' not in os.environ and LOCAL_CONFIG_PATH.is_file():
        try:
            for line in LOCAL_CONFIG_PATH.read_text(encoding='utf-8-sig').splitlines():
                key, separator, value = line.partition('=')
                if separator and key.strip() == 'SEC_CONTACT_EMAIL':
                    local_value = value.strip().strip('"').strip("'")
        except OSError:
            raise SourceError('Could not read local SEC identity configuration.') from None
    value = os.environ.get('SEC_CONTACT_EMAIL', local_value)
    match = re.fullmatch(r'([A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+)@((?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63})', value)
    invalid = True
    if match:
        local, domain = match.group(1).lower(), match.group(2).lower()
        reserved = any(domain == suffix or domain.endswith('.'+suffix) for suffix in ('example.com', 'example.org', 'example.net')) or domain.endswith(('.invalid', '.test', '.example', '.localhost'))
        placeholder = any(term in local for term in ('placeholder', 'your_email', 'your-email', 'real_authorized_contact', 'noreply', 'no-reply'))
        github_noreply = domain == 'noreply.github.com' or domain.endswith('.noreply.github.com')
        invalid = reserved or placeholder or github_noreply or local.startswith('.') or local.endswith('.') or '..' in local
    if invalid or any(char in value for char in '\r\n'):
        raise SourceError('Live SEC retrieval requires SEC_CONTACT_EMAIL containing a real monitored owner-approved bare email in Git-ignored .env.local or server environment; placeholder and noreply contacts are not permitted. Organization is ClaimTrace Hackathon Team.')
    return f'ClaimTrace Hackathon Team {value}'


def get_json(url):
    global _last
    user_agent = sec_user_agent()
    with _lock:
        time.sleep(max(0, .5 - (time.monotonic() - _last)))
        _last = time.monotonic()
        try:
            with httpx.stream('GET', url, headers={'User-Agent': user_agent, 'Accept-Encoding': 'gzip, deflate'}, timeout=20, follow_redirects=False) as response:
                response.raise_for_status()
                payload = bytearray()
                for chunk in response.iter_bytes():
                    payload.extend(chunk)
                    if len(payload) > 15_000_000:
                        raise SourceError('SEC response exceeded the 15 MB bound.')
            return json.loads(payload), hashlib.sha256(payload).hexdigest()
        except (httpx.HTTPError, ValueError, RecursionError):
            raise SourceError('SEC unavailable or returned invalid data; no evidence was invented.') from None


def cached_evidence(request):
    raw = DATA.read_bytes()
    snapshot = json.loads(raw)
    if request.company.cik.zfill(10) != snapshot['company']['cik'] or request.fiscal_year != 2026 or request.period != 'Q2':
        return None
    request.company.name = snapshot['company']['name']
    request.company.ticker = snapshot['company']['ticker']
    sources = {source['source_id']: source for source in snapshot['sources']}
    result = []
    for row in snapshot['records']:
        if row['duration'] != 'quarter' or row['period_end'] != '2026-06-30':
            continue
        if date.fromisoformat(row['filed_date']) > request.as_of:
            continue
        source = sources[row['source_id']]
        result.append(Evidence(id=row['evidence_id'], document=f"SEC {source['form']} {source['accession']}",
            url=row['source_url'], published_at=row['filed_date'], period_start=row['period_start'], period_end=row['period_end'],
            unit=row['unit'], value=row['value'], concept=row['concept'], locator=json.dumps(row['source_locator'], sort_keys=True),
            source_mode='cached_sec', source_sha256=source['sha256']))
    # A filing can contain comparative facts: do not label older concept values as this period.
    if result:
        target_end = max(e.period_end for e in result)
        result = [e for e in result if e.period_end == target_end]
    return result


def companyfacts_evidence(request, payload, digest, report_dates=None):
    if not isinstance(payload, dict):
        raise SourceError('SEC Companyfacts returned an invalid structure.')
    if str(payload.get('cik', '')).zfill(10) != request.company.cik.zfill(10):
        raise SourceError('SEC returned an unexpected company CIK.')
    result = []
    report_dates = report_dates or {}
    fact_groups = payload.get('facts', {})
    if not isinstance(fact_groups, dict) or not isinstance(fact_groups.get('us-gaap', {}), dict):
        raise SourceError('SEC Companyfacts returned an invalid facts structure.')
    facts = fact_groups.get('us-gaap', {})
    for concept in CONCEPTS:
        candidates = []
        item = facts.get(concept, {})
        if not isinstance(item, dict) or not isinstance(item.get('units', {}), dict):
            raise SourceError('SEC Companyfacts returned invalid units.')
        for unit, rows in item.get('units', {}).items():
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise SourceError('SEC Companyfacts returned invalid fact rows.')
            for row in rows:
                try:
                    start, end, filed = (date.fromisoformat(row[k]) for k in ('start', 'end', 'filed'))
                    days = (end - start).days + 1
                    duration_matches = 330 <= days <= 380 if request.period == 'FY' else 70 <= days <= 105
                    if (re.fullmatch(r'\d{10}-\d{2}-\d{6}', str(row.get('accn', '')))
                            and row.get('fy') == request.fiscal_year and row.get('fp') == request.period
                            and duration_matches and filed <= request.as_of and end <= request.as_of
                            and report_dates.get(row.get('accn')) == row['end']
                            and row.get('form') in ('10-Q', '10-K')):
                        candidates.append((end, filed, unit, row))
                except (KeyError, ValueError, TypeError):
                    continue
        if not candidates:
            continue
        # SEC fy/fp describe the reporting filing; choose latest period, avoiding its comparative rows.
        end, filed, unit, row = max(candidates, key=lambda x: (x[0], x[1]))
        accession = row['accn']
        url = f"https://www.sec.gov/Archives/edgar/data/{int(request.company.cik)}/{accession.replace('-', '')}/{accession}-index.html"
        try:
            result.append(Evidence(id=f"{concept}-{row['start']}-{row['end']}", document=f"SEC {row['form']} {accession}", url=url,
                published_at=filed, period_start=row['start'], period_end=end, unit=unit, value=row['val'], concept=concept,
                locator=f"Companyfacts us-gaap/{concept}/{unit}; accession={accession}; start={row['start']}; end={row['end']}",
                source_mode='live_sec', source_sha256=digest))
        except (KeyError, TypeError, ValueError):
            raise SourceError('SEC financial evidence failed validation.') from None
    if result:
        target_end = max(e.period_end for e in result)
        result = [e for e in result if e.period_end == target_end]
    return result


def sec_evidence(request: InvestigationRequest):
    if os.getenv('CLAIMTRACE_SEC_MODE', 'cache_first') != 'live':
        cached = cached_evidence(request)
        if cached is not None:
            return cached
    payload, digest = get_json(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{request.company.cik.zfill(10)}.json')
    submissions, _ = get_json(f'https://data.sec.gov/submissions/CIK{request.company.cik.zfill(10)}.json')
    try:
        if not isinstance(submissions, dict) or str(submissions['cik']).zfill(10) != request.company.cik.zfill(10):
            raise ValueError
        recent = submissions['filings']['recent']
        report_dates = dict(zip(recent['accessionNumber'], recent['reportDate']))
        tickers = submissions.get('tickers', [])
        if not isinstance(tickers, list) or not tickers:
            raise ValueError
        request.company = Company(name=submissions['name'], ticker=tickers[0], cik=request.company.cik.zfill(10))
    except (KeyError, TypeError, ValueError):
        raise SourceError('SEC submissions metadata is invalid; reporting dates could not be verified.') from None
    return companyfacts_evidence(request, payload, digest, report_dates)
