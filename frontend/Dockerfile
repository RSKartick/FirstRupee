# FirstRupee web app (SvelteKit, Node adapter). Build from the repository root: docker build -f frontend/Dockerfile frontend
FROM node:22-alpine AS build
WORKDIR /srv/web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build && npm prune --omit=dev

FROM node:22-alpine
ENV NODE_ENV=production HOST=0.0.0.0 PORT=3000 BACKEND_URL=http://api:8000
WORKDIR /srv/web
COPY --from=build /srv/web/build ./build
COPY --from=build /srv/web/node_modules ./node_modules
COPY --from=build /srv/web/package.json ./package.json
EXPOSE 3000
CMD ["node", "build/index.js"]
