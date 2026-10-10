# Multi-stage Dockerfile for News Sentiment Analyzer Frontend Dashboard

# -------------------------------------------------------------------
# Stage 1: Build static assets
# -------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency specifications
COPY package.json package-lock.json ./

# Install npm dependencies cleanly
RUN npm ci

# Copy application sources
COPY . .

# Typecheck and compile production bundle
RUN npm run build

# -------------------------------------------------------------------
# Stage 2: Serve via Nginx
# -------------------------------------------------------------------
FROM nginx:alpine AS runtime

# Remove default nginx HTML files
RUN rm -rf /usr/share/nginx/html/*

# Copy build artifacts
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom reverse-proxy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose web server port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

# Start nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
