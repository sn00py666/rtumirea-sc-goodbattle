FROM node:lts-slim AS base
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable
COPY . /app
WORKDIR /app

FROM base AS prod-deps
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --prod --frozen-lockfile

FROM base AS build
RUN --mount=type=cache,id=pnpm,target=/pnpm/store pnpm install --frozen-lockfile

RUN pnpm generate-api-types
RUN pnpm build

FROM nginx:alpine

RUN echo "ICAgICAgd29ya2VyX3Byb2Nlc3NlcyA0OwoKICAgICAgZXZlbnRzIHsgd29ya2VyX2Nvbm5lY3Rpb25zIDEwMjQ7IH0KCiAgICAgIGh0dHAgewogICAgICAgICAgbGFyZ2VfY2xpZW50X2hlYWRlcl9idWZmZXJzIDggNjRrOwogICAgICAgICAgY2xpZW50X2hlYWRlcl9idWZmZXJfc2l6ZSAgIDhrOwoKICAgICAgICAgIHNlcnZlciB7CiAgICAgICAgICAgICAgbGlzdGVuIDgwOwogICAgICAgICAgICAgIHJvb3QgIC91c3Ivc2hhcmUvbmdpbngvaHRtbDsKICAgICAgICAgICAgICBpbmNsdWRlIC9ldGMvbmdpbngvbWltZS50eXBlczsKCiAgICAgICAgICAgICAgZ3ppcCBvbjsgCiAgICAgICAgICAgICAgZ3ppcF92YXJ5IG9uOyAKICAgICAgICAgICAgICBnemlwX21pbl9sZW5ndGggMTAyNDsgCiAgICAgICAgICAgICAgZ3ppcF90eXBlcyB0ZXh0L3BsYWluIHRleHQvY3NzIHRleHQveG1sIHRleHQvamF2YXNjcmlwdCBhcHBsaWNhdGlvbi94LWphdmFzY3JpcHQgYXBwbGljYXRpb24veG1sOyAKICAgICAgICAgICAgICBnemlwX2Rpc2FibGUgIk1TSUUgWzEtNl1cLiI7CgogICAgICAgICAgICAgIGxvY2F0aW9uIC8gewogICAgICAgICAgICAgICAgICB0cnlfZmlsZXMgJHVyaSAkdXJpLyAkdXJpL2luZGV4Lmh0bWwgJHVyaS5odG1sIC9pbmRleC5odG1sID00MDQ7CiAgICAgICAgICAgICAgfQogICAgICAgICAgfQogICAgICB9" | base64 -d > /etc/nginx/nginx.conf

RUN rm -rf /usr/share/nginx/html/*
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
