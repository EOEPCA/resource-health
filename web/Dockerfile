FROM node:22 AS build

WORKDIR /app

COPY ./tsconfig.json ./yarn.lock ./next-env.d.ts ./postcss.config.mjs ./.gitignore ./next.config.mjs ./tailwind.config.ts ./.eslintrc.json ./package.json /app/
COPY ./src/ /app/src/

RUN yarn install
RUN yarn build

FROM node:22-alpine AS runtime

WORKDIR /app

COPY package*.json /app
RUN npm ci --only=production

COPY --from=build /app/.next /app/.next

EXPOSE 3000
ENTRYPOINT ["yarn"]
CMD ["start"]
