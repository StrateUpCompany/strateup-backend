# StrateUp Backend

Backend Fastify + TypeScript + Prisma + Supabase

## Requisitos

- Node.js >= 20.x
- Docker e Docker Compose

## Setup local

```bash
cp .env.example .env
docker-compose up --build
# Em outro terminal:
docker-compose exec app npx prisma migrate dev
docker-compose exec app npx prisma generate
```

Acesse: [http://localhost:3000/health](http://localhost:3000/health)

Acesse docs Swagger: [http://localhost:3000/docs](http://localhost:3000/docs)

## Estrutura de pastas

```
src/
  controllers/
  routes/
  services/
  repositories/
  middlewares/
  schemas/
  utils/
  index.ts
prisma/
  schema.prisma
  migrations/
tests/
.env
```

## Comandos úteis

- `npm run dev` — modo desenvolvimento
- `npm run build` — build TypeScript
- `npm run start` — produção
- `npm run lint` — lint
- `npm run format` — prettier
- `npm run test` — testes
- `npm run prisma:migrate` — migration
- `npm run prisma:generate` — gerar client Prisma
- `npm run prisma:studio` — visualização do banco