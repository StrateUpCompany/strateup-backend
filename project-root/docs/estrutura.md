Stack Principal Decidida
Node.js + TypeScript (runtime e linguagem)
Fastify (framework web para APIs REST, com performance, validação e TS nativos)
Prisma (ORM moderno para PostgreSQL/Supabase)
Supabase (PostgreSQL) (backend-as-a-service: banco, auth, storage)
Supabase Auth (autenticação integrada)
Docker (containerização e ambiente local uniformizado)
Swagger/OpenAPI (documentação e contrato de API automáticos)
Jest (testes automatizados)
ESLint/Prettier (qualidade e padronização de código)
supabase-js (SDK de integração, se necessário, no backend e frontend)


/project-root
│
├── src/                    # Código-fonte principal
│   ├── controllers/        # Handlers das rotas
│   ├── routes/             # Definição de rotas Fastify
│   ├── services/           # Lógica de negócio
│   ├── repositories/       # Interação com Prisma (banco)
│   ├── middlewares/        # Middlewares Fastify
│   ├── schemas/            # Schemas de validação (Zod/JSON Schema)
│   ├── utils/              # Funções utilitárias
│   └── index.ts            # Ponto de entrada do app
│
├── prisma/                 # Schema e migrations do Prisma
│   ├── schema.prisma
│   └── migrations/
│
├── tests/                  # Testes automatizados (Jest)
│
├── docs/                   # Documentação (OpenAPI, extras)
│
├── .env.example            # Variáveis de ambiente de exemplo
├── docker-compose.yml      # Docker para ambiente local
├── Dockerfile              # Docker para build da aplicação
├── package.json            
├── tsconfig.json           # Configuração TypeScript
└── README.md