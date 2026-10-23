-- REVIEWABLE CANDIDATE ONLY. NOT EXECUTED. Use recorded scoped owner approval.
-- Scope approved 2026-10-23; a real owner-approved SEC contact is still required.
-- Official syntax: https://raw.githubusercontent.com/zetaris/getting-started/main/open_data/rest_apis/sql/rate_limited/01_edgar_company_facts_create.sql
-- Scope: one isolated Lightning DB, one SchemaStore container, three REST
-- registrations, one view. No overwrites/grants/cache/pipeline/AWS resources.
-- Inspect object names first. Stop if any exists; do not replace existing data.
-- Supply REAL_AUTHORIZED_CONTACT locally before execution (not a secret).
-- SEC egress and supported create privileges must already exist; do not expand.
CREATE LIGHTNING DATABASE CLAIMTRACE DESCRIBE BY "ClaimTrace SEC financial evidence";
CREATE SCHEMASTORE CONTAINER claimtrace;

CREATE LIGHTNING REST TABLE isrg_revenue_facts FROM CLAIMTRACE REQUEST(
 endpoint "https://data.sec.gov/api/xbrl/companyconcept/CIK0001035267/us-gaap/RevenueFromContractWithCustomerExcludingAssessedTax.json",
 method "get", response_type "json", http_encoding "URLENCODED"
) HEADER (user-agent "ClaimTrace REAL_AUTHORIZED_CONTACT") BODY ();

CREATE LIGHTNING REST TABLE isrg_eps_facts FROM CLAIMTRACE REQUEST(
 endpoint "https://data.sec.gov/api/xbrl/companyconcept/CIK0001035267/us-gaap/EarningsPerShareDiluted.json",
 method "get", response_type "json", http_encoding "URLENCODED"
) HEADER (user-agent "ClaimTrace REAL_AUTHORIZED_CONTACT") BODY ();

CREATE LIGHTNING REST TABLE isrg_netincome_facts FROM CLAIMTRACE REQUEST(
 endpoint "https://data.sec.gov/api/xbrl/companyconcept/CIK0001035267/us-gaap/NetIncomeLoss.json",
 method "get", response_type "json", http_encoding "URLENCODED"
) HEADER (user-agent "ClaimTrace REAL_AUTHORIZED_CONTACT") BODY ();

CREATE SCHEMASTORE VIEW sec_financial_evidence WITH CONTAINER claimtrace AS
SELECT concat('ISRG-revenue-', fact.`start`, '-', fact.`end`) AS evidence_id,
 '0001035267' AS cik, 'Intuitive Surgical, Inc.' AS company_name, 'ISRG' AS ticker,
 year(to_date(fact.`end`)) AS fiscal_year, 'Q2' AS fiscal_period,
 to_date(fact.`end`) AS reporting_period_end,
 concat('SEC ', fact.form, ' ', fact.accn) AS document,
 'https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm' AS source_url,
 to_date(fact.filed) AS published_at, to_date(fact.`start`) AS period_start,
 to_date(fact.`end`) AS period_end, 'USD' AS unit,
 cast(fact.val AS DECIMAL(28,8)) AS value, 'RevenueFromContractWithCustomerExcludingAssessedTax' AS concept,
 concat('Companyconcept RevenueFromContractWithCustomerExcludingAssessedTax; accession=', fact.accn, '; start=', fact.`start`, '; end=', fact.`end`) AS locator,
 cast(NULL AS STRING) AS source_sha256
FROM CLAIMTRACE.isrg_revenue_facts
LATERAL VIEW explode(units.USD) AS fact
WHERE fact.accn = '0001035267-26-000058' AND ((fact.`start` = '2026-04-01' AND fact.`end` = '2026-06-30') OR (fact.`start` = '2025-04-01' AND fact.`end` = '2025-06-30'))
UNION ALL
SELECT concat('ISRG-eps-', fact.`start`, '-', fact.`end`) AS evidence_id,
 '0001035267' AS cik, 'Intuitive Surgical, Inc.' AS company_name, 'ISRG' AS ticker,
 year(to_date(fact.`end`)) AS fiscal_year, 'Q2' AS fiscal_period,
 to_date(fact.`end`) AS reporting_period_end,
 concat('SEC ', fact.form, ' ', fact.accn) AS document,
 'https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm' AS source_url,
 to_date(fact.filed) AS published_at, to_date(fact.`start`) AS period_start,
 to_date(fact.`end`) AS period_end, 'USD/shares' AS unit,
 cast(fact.val AS DECIMAL(28,8)) AS value, 'EarningsPerShareDiluted' AS concept,
 concat('Companyconcept EarningsPerShareDiluted; accession=', fact.accn, '; start=', fact.`start`, '; end=', fact.`end`) AS locator,
 cast(NULL AS STRING) AS source_sha256
FROM CLAIMTRACE.isrg_eps_facts
LATERAL VIEW explode(units.`USD/shares`) AS fact
WHERE fact.accn = '0001035267-26-000058' AND ((fact.`start` = '2026-04-01' AND fact.`end` = '2026-06-30') OR (fact.`start` = '2025-04-01' AND fact.`end` = '2025-06-30'))
UNION ALL
SELECT concat('ISRG-netincome-', fact.`start`, '-', fact.`end`) AS evidence_id,
 '0001035267' AS cik, 'Intuitive Surgical, Inc.' AS company_name, 'ISRG' AS ticker,
 year(to_date(fact.`end`)) AS fiscal_year, 'Q2' AS fiscal_period,
 to_date(fact.`end`) AS reporting_period_end,
 concat('SEC ', fact.form, ' ', fact.accn) AS document,
 'https://www.sec.gov/Archives/edgar/data/1035267/000103526726000058/isrg-20260630.htm' AS source_url,
 to_date(fact.filed) AS published_at, to_date(fact.`start`) AS period_start,
 to_date(fact.`end`) AS period_end, 'USD' AS unit,
 cast(fact.val AS DECIMAL(28,8)) AS value, 'NetIncomeLoss' AS concept,
 concat('Companyconcept NetIncomeLoss; accession=', fact.accn, '; start=', fact.`start`, '; end=', fact.`end`) AS locator,
 cast(NULL AS STRING) AS source_sha256
FROM CLAIMTRACE.isrg_netincome_facts
LATERAL VIEW explode(units.USD) AS fact
WHERE fact.accn = '0001035267-26-000058' AND ((fact.`start` = '2026-04-01' AND fact.`end` = '2026-06-30'));

-- Read-only acceptance after individually checking each registration and view.
-- These fiscal labels derive from the explicit ISRG quarter pairs, not the
-- filing's fy/fp (which also label comparative/YTD records).
SELECT evidence_id, cik, company_name, ticker, fiscal_year, fiscal_period, reporting_period_end,
       document, source_url, published_at, period_start, period_end,
       unit, value, concept, locator, source_sha256
FROM claimtrace.sec_financial_evidence
WHERE cik = '0001035267' AND fiscal_year = 2026 AND fiscal_period = 'Q2'
  AND published_at <= '2026-10-23'
LIMIT 25;
-- Expect current-quarter revenue 2892300000 USD, EPS 2.29 USD/shares,
-- GAAP net income 818100000 USD. API should return3 current records; view5 total.
-- Configure CLAIMTRACE_ZETARIS_TABLE=claimtrace.sec_financial_evidence only AFTER
-- successful approved creation + measured read. No script executes this file.
-- Cloud REST registrations can refetch SEC on reads; SQL LIMIT is not an SEC
-- request-rate bound. Execute sequentially, <5 SEC requests/sec, max2 repair cycles.
