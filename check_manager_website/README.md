## Getting Started

First install yarn by following https://yarnpkg.com/getting-started/install step 1.
That's right, just call `corepack enable` and it should work if you have a modern node js installed.
If you have trouble here, see https://yarnpkg.com/corepack


Run the check api first. For how to do that, see `check_manager/README.md`

Then, run the development server:

```bash
NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT=http://localhost:8000/v1 NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:12345/v1 yarn dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

## Production

Make sure you set the environment variable `NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT`, and then run

```bash
yarn build
yarn start
```

## Docker image

From the current directory build the image with

```bash
docker build -t check_manager_website -f Dockerfile .
```

Run the image with

```bash
docker run -e NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT=http://localhost:8000/v1 -e NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:12345/v1 -p 3000:3000 -it check_manager_website
```

Where `NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT` points to the REST API endpoint.