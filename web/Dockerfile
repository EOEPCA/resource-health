FROM node:22

WORKDIR /app

COPY ./tsconfig.json ./yarn.lock ./next-env.d.ts ./postcss.config.mjs ./.gitignore ./next.config.mjs ./tailwind.config.ts ./.eslintrc.json ./package.json /app/

RUN yarn install

COPY ./src/ /app/src/

ENTRYPOINT [ "yarn", "dev" ]