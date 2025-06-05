# Check Manager Website

Web UI for managing and inspecting checks and their outcomes

## Getting Started

First install yarn by following https://yarnpkg.com/getting-started/install step 1.
That's right, just call `corepack enable` and it should work if you have a modern node js installed.
If you have trouble here, see https://yarnpkg.com/corepack

Run the check REST api first. For how to do that, see [../check_manager/README.md](../check_manager/README.md)

Install the dependencies by running

```bash
yarn install
```

You will only need to run that again if dependencies or their versions are changed.

Then, run the development server:

```bash
NEXT_PUBLIC_TELEMETRY_DURATION_DAYS=500 NEXT_PUBLIC_RELOGIN_URL=http://localhost:3000/login NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT=http://localhost:8000/v1 NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:12345/v1 yarn dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying [src/app/page.tsx](src/app/page.tsx). The page auto-updates as you edit the file.

## Production

Run

```
yarn build
```

Then make sure you set the environment variables `NEXT_PUBLIC_RELOGIN_URL`, `NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT`, and `NEXT_PUBLIC_TELEMETRY_ENDPOINT`, (also optionally set `NEXT_PUBLIC_TELEMETRY_DURATION_DAYS`) and then run

```bash
yarn start
```

## Docker image

From the current directory build the image with

```bash
docker build -t check_manager_website -f Dockerfile .
```

Run the image with

```bash
docker run -e NEXT_PUBLIC_TELEMETRY_DURATION_DAYS=5 -e NEXT_PUBLIC_RELOGIN_URL=http://localhost:3000/login -e NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT=http://localhost:8000/v1 -e NEXT_PUBLIC_TELEMETRY_ENDPOINT=http://localhost:12345/v1 -p 3000:3000 -it check_manager_website
```
