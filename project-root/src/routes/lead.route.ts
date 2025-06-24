import { FastifyInstance } from 'fastify';
import { verifyJwt } from '../middlewares/auth';
import { LeadRepository } from '../repositories/lead.repository';

export async function leadRoutes(fastify: FastifyInstance) {
  fastify.get('/leads', {
    preHandler: [verifyJwt],
    schema: {
      tags: ['Lead'],
      summary: 'Listar leads',
      security: [{ bearerAuth: [] }],
      response: {
        200: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              id: { type: 'number' },
              name: { type: 'string' },
              email: { type: 'string' },
              funnelId: { type: 'number' },
              ownerId: { type: 'number' }
            }
          }
        }
      }
    }
  }, async () => LeadRepository.findAll());

  fastify.post('/leads', {
    preHandler: [verifyJwt],
    schema: {
      tags: ['Lead'],
      summary: 'Criar lead',
      security: [{ bearerAuth: [] }],
      body: {
        type: 'object',
        required: ['name', 'email', 'funnelId', 'ownerId'],
        properties: {
          name: { type: 'string' },
          email: { type: 'string' },
          funnelId: { type: 'number' },
          ownerId: { type: 'number' }
        }
      },
      response: {
        201: {
          type: 'object',
          properties: {
            id: { type: 'number' },
            name: { type: 'string' },
            email: { type: 'string' },
            funnelId: { type: 'number' },
            ownerId: { type: 'number' }
          }
        }
      }
    }
  }, async (req, reply) => {
    const { name, email, funnelId, ownerId } = req.body as any;
    const lead = await LeadRepository.create({ name, email, funnelId, ownerId });
    reply.code(201);
    return lead;
  });

  // PUT e DELETE implementações similares...
}