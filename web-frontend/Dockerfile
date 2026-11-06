# Base Image Node.js 18
FROM node:20-alpine

WORKDIR /app

# Salin package json
COPY package*.json ./

# Install dependensi frontend
RUN npm install

# Salin seluruh kodingan web
COPY . .

# Build Next.js
RUN npm run build

# Buka port 3000
EXPOSE 3000

# Jalankan server frontend
CMD ["npm", "start"]