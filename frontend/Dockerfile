FROM node:20-alpine

WORKDIR /app

# Accept build arguments for Vite environment variables
ARG VITE_API_BASE_URL
ARG VITE_GOOGLE_CLIENT_ID

# Set environment variables for Vite
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID

# Copy package manifests and install dependencies
COPY package*.json ./
RUN npm install

# Copy application source files
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start Vite dev server on host 0.0.0.0
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
