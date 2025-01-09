FROM node:22 AS build

ENV NEXT_PUBLIC_CHECK_MANAGER_ENDPOINT=

WORKDIR /app

COPY ./tsconfig.json ./yarn.lock ./.yarnrc.yml ./next-env.d.ts ./postcss.config.mjs ./.gitignore ./next.config.mjs ./next.config.ts ./tailwind.config.ts ./.eslintrc.json ./package.json /app/
COPY ./src/ /app/src/

RUN corepack enable && yarn install --immutable
RUN yarn build

FROM node:22-alpine AS runtime

WORKDIR /app

COPY package.json yarn.lock /app/
RUN corepack enable && yarn workspaces focus --production && yarn install --immutable

COPY --from=build /app/.next /app/.next

EXPOSE 3000
ENTRYPOINT ["yarn"]
CMD ["start"]
