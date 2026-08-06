# Limitations and responsible-use statement

1. All patient, member, provider, coverage, and claim records are synthetic.
2. Synthetic accuracy cannot establish performance on real payer populations.
3. The CMS/eCFR knowledge base is a curated subset, not a complete legal corpus.
4. Policy text is a cited summary and must be validated against the current
   authoritative document before real use.
5. COB rules are representative demonstrations, not legal advice.
6. The model uses synthetic assumptions that may not transfer to real claims.
7. The LLM is optional and cannot authorize payment, denial, or recovery.
8. The default local database and policy search are SQLite/TF-IDF; PostgreSQL/pgvector configuration is supplied
   but was not container-tested because Docker is unavailable locally.
9. Seeded credentials, the local signing secret, and browser token storage are
   demonstration controls, not production identity architecture.
10. No HIPAA, SOC 2, penetration-test, accessibility, or regulatory
    certification is claimed.
11. ROI figures are user-controlled scenarios, not guaranteed savings.
12. Real deployment requires licensed data access, legal review, calibration,
    fairness analysis, drift monitoring, SSO, encryption, and operational SLAs.
13. The EDI-like format is intentionally simplified and is not certified ANSI X12 837 parsing.
14. The custom synthetic generator covers the project scenarios but is not a full Synthea distribution.
