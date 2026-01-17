# Bank Surveillance Tests

Tests specific to the bank surveillance use case.

## Use Case Requirements
- USE_CASE=bank_surveillance
- Plugins: geographic_boundaries, hierarchical_teams, data_classification

## Resources Tested
- communications
- investigations
- alerts
- surveillance_reports

## Running
```bash
make test-b2b-bank
# or
docker-compose run --rm e2e-tests env USE_CASE=bank_surveillance pytest tests/e2e_api/b2b/bank_surveillance -v
```
