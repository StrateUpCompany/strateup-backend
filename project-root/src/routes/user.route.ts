import { FastifyInstance } from 'fastify';
import { verifyJwt } from '../middlewares/auth';
import { UserRepository } from '../repositories/user.repository';

export async function userRoutes(fastify: FastifyInstance) {
  // GET /users
  fastify.get('/users', {
    preHandler: [verifyJwt],
    schema: {
      description: 'Lista todos os usuários (protegido por JWT)',
      tags: ['User'],
      summary: 'Listar usuários autenticado',
      security: [{ bearerAuth: [] }],
      response: {
        200: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              id: { type: 'number' },
              email: { type: 'string' },
              name: { type: 'string' }
            }
          }
        }
      }
    }
  }, async () => {
    return UserRepository.findAll();
  });

  // POST /users
  fastify.post('/users', {
    preHandler: [verifyJwt],
    schema: {
      description: 'Cria um novo usuário',
      tags: ['User'],
      summary: 'Criar usuário',
      security: [{ bearerAuth: [] }],
      body: {
        type: 'object',
        required: ['email', 'name'],
        properties: {
          email: { type: 'string' },
          name: { type: 'string' }
        }
      },
      response: {
        201: {
          type: 'object',
          properties: {
            id: { type: 'number' },
            email: { type: 'string' },
            name: { type: 'string' }
          }
        }
      }
    }
  }, async (request, reply) => {
    const { email, name } = request.body as any;
    const user = await UserRepository.create({ email, name });
    reply.code(201);
    return user;
  });

  // PUT /users/:id
  fastify.put('/users/:id', {
    preHandler: [verifyJwt],
    schema: {
      description: 'Atualiza um usuário',
      tags: ['User'],
      summary: 'Atualizar usuário',
      security: [{ bearerAuth: [] }],
      params: {
        type: 'object',
        properties: {
          id: { type: 'integer' }
        },
        required: ['id']
      },
      body: {
        type: 'object',
        properties: {
          email: { type: 'string' },
          name: { type: 'string' }
        }
      },
      response: {
        200: {
          type: 'object',
          properties: {
            id: { type: 'number' },
            email: { type: 'string' },
            name: { type: 'string' }
          }
        }
      }
    }
  }, async (request, reply) => {
    const id = Number((request.params as any).id);
    const { email, name } = request.body as any;
    const user = await UserRepository.update(id, { email, name });
    return user;
  });

  // DELETE /users/:id
  fastify.delete('/users/:id', {
    preHandler: [verifyJwt],
    schema: {
      description: 'Remove um usuário',
      tags: ['User'],
      summary: 'Remover usuário',
      security: [{ bearerAuth: [] }],
      params: {
        type: 'object',
        properties: {
          id: { type: 'integer' }
        },
        required: ['id']
      },
      response: {
        204: {
          type: 'null'
        }
      }
    }
  }, async (request, reply) => {
    const id = Number((request.params as any).id);
    await UserRepository.delete(id);
    reply.code(204).send();
  });
}