# R2 smoke test

The manual GitHub Actions workflow **R2 Smoke Test** verifies the temporary-media
bucket without storing workflow artifacts.

It performs only:

1. create one short-lived presigned PUT URL;
2. upload a tiny text payload;
3. read it back through a signed GET URL;
4. delete the object through a signed DELETE URL;
5. verify that the object is no longer readable.

Required repository Actions secrets:

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET`

The workflow never prints secret values and uploads no GitHub artifact.
