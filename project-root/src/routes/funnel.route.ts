import { FastifyInstance } from 'fastify';
import { verifyJwt } from '../middlewares/auth';
import { FunnelRepository } from '../repositories/funnel.repository';

export async function funnelRoutes(fastify: FastifyInstance) {
  fastify.get('/funnels', {
    preHandler: [verifyJwt],
    schema: {
      tags: ['Funnel'],
      summary: 'Listar funis',
      security: [{ bearerAuth: [] }],
      response: {
        200: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              id: { type: 'number' },
              name: { type: 'string' },
              description: { type: 'string' }
            }
          }
        }
      }
    }
  }, async () => FunnelRepository.findAll());

  fastify.post('/funnels', {
    preHandler: [verifyJwt],
    schema: {
      tags: ['Funnel'],
      summary: 'Criar funil',
      security: [{ bearerAuth: [] }],
      body: {
        type: 'object',
        required: ['name'],
        properties: { name: { type: 'string' }, description: { type: 'string' } }
      },
      response: {
        201: {
          type: 'object',
          properties: { id: { type: 'number' }, name: { type: 'string' }, description: { type: 'string' } }
        }
      }
    }
  }, async (req, reply) => {
    const { name, description } = req.body as any;
    const funnel = await FunnelRepository.create({ name, description });
    reply.code(201);
    return funnel;
  });

  // PUT e DELETE implementações similares...
}