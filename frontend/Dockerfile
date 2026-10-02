# AGROTECH frontend — build Vite + Nginx estático (multi-stage).
# VITE_API_URL se fija en build: "" = mismo origen (Nginx proxya /api al backend).
ARG VITE_API_URL=""

FROM node:22-alpine AS build
ARG VITE_API_URL
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
