# H-02 preparation and actual reproduction

## Historical source-only stage1 command

Existing Python3.12 environment; no .env, Docker, DB, provider credential or new model needed.
Target source includes current H-01 changes. This does not start WhyYou/worker or run actual H-02.

```powershell
.venv/Scripts/python.exe -m scripts.h02_prepare --whyyou-repo ../gbsa_aws
.venv/Scripts/python.exe -m scripts.h02_prepare --whyyou-repo ../gbsa_aws --output .controlproof/h02-preparation.json
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider tests/contract/test_h02_source_inventory.py tests/unit/test_h02_preparation.py --basetemp .controlproof/test-tmp/h02-preparation
```

Output always H-02/stage1/NOT_RUN/product_verdict:null. READY_FOR_REVIEW means only that the bounded
collector resolved its inventory; BLOCKED means incomplete source/connection/parse/drift facts.
Neither means product PASS/FAIL. Every entry UNREVIEWED. Exit2 is expected for the current workspace:
privacy_deletion's indirect runtime attribute needs actual binding verification. Do not suppress it.
Optional output must be outside the target repository. Raw preparation stays ignored.

At the stage1 checkpoint, official engine.cli run H-02 was not registered. Current stage2 uses H02_CAPABILITY_SURFACE_V1 (below). Stage2 needs actual bindings, clean frozen sources,
assessment/evidence/cleanup contracts, first-result preservation and UI QA. This unsealed preparation
JSON is not a finished bundle. See inventory-review.md/source baseline/validation.md.

## Stage2 actual reproduction

Use clean reviewed validation sources, Docker Desktop and the existing WhyYou Python environment.
Keep runtime state outside both repositories. Do not reuse stage1 preparation JSON as a Run.
New target source bytes require an explicit source review and ledger entry; unknown versions block
PASS. The shipped source review supports the first and remedied trees recorded in actual-closure.md.

From a clean ControlProof checkout (replace paths/ports with your isolated local paths):

```powershell
python -m scripts.h02_local up --instance h02-check --whyyou-repo <clean-whyyou> --whyyou-python <whyyou-python> --state-root <outside-source-state> --pg-port 15738 --aws-port 14771 --api-port 18089
python -m scripts.h02_local cli --instance h02-check --state-root <outside-source-state> -- preflight H-02 --profile H02_CAPABILITY_SURFACE_V1 --target whyyou-local --json
python -m scripts.h02_local cli --instance h02-check --state-root <outside-source-state> -- run H-02 --profile H02_CAPABILITY_SURFACE_V1 --target whyyou-local --operator local-reviewer --label h02-check --json
python -m scripts.h02_local cli --instance h02-check --state-root <outside-source-state> -- verify <run-id> --json
python -m scripts.h02_local stop --instance h02-check --state-root <outside-source-state>
```

Inspect READY first. Preserve a first FAIL; fix only afterward, freeze new sources, and use
`retest <parent-run-id> --target whyyou-local --operator local-reviewer --label <label> --json`.
Parent bundles must be available byte-identically in the selected run root. No web Run button.
The wrapper supplies H02 fixed model/isolation and ephemeral synthetic constructor credentials;
no real GCP credentials or external AI calls are required. Never persist environment/key material.

Final recorded viewer: http://localhost:8766/runs/c12c2ce8-f607-4be3-9524-0dec27dc7260.
Original execution dates/SHAs/hashes/limitations stay in actual-closure.md and validation.md.
