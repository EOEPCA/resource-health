FROM node:22

WORKDIR /app

COPY ./tsconfig.json ./yarn.lock ./next-env.d.ts ./postcss.config.mjs ./.gitignore ./next.config.mjs ./tailwind.config.ts ./.eslintrc.json ./package.json /app/

RUN yarn install

COPY ./src/app/page.tsx ./src/app/globals.css ./src/app/layout.tsx /app/app

ENTRYPOINT [ "yarn", "dev" ]