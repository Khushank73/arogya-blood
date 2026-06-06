# Dockerfile for Next.js frontend
FROM node:18-alpine

WORKDIR /app

# Install dependencies first (leverage docker cache)
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps

# Copy source files
COPY frontend/ ./

# Disable Next telemetry during build
ENV NEXT_TELEMETRY_DISABLED=1

# Build the Next.js app
RUN npm run build

# Expose Next dev/start port
EXPOSE 3000

CMD ["npm", "run", "start"]
