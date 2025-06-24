import { FastifyInstance } from 'fastify';
import { verifyJwt } from '../middlewares/auth';
import { AutomationRepository } from '../repositories/automation.repository';

export async function automationRoutes(fastify: FastifyInstance) {
  fastify.get('/automations', {
    preHandler: [verifyJwt],
    schema: {
      tags: ['Automation'],
      summary: 'Listar automações',
      security: [{ bearerAuth: [] }],
      response: {
        200: {
          type: 'array',
          items: {
            type: 'object',
            properties: {
              id: { type: 'number' },
              name: { type: 'string' },
              description: { type: 'string' },
              funnelId: { type: 'number' },
              triggers: { type: 'object' },
              actions: { type: 'object' },
              createdAt: { type: 'string', format: 'date-time' },
              updatedAt: { type: 'string', format: 'date-time' }
            }
          }
        }
      }
    }
  }, async () => AutomationRepository.findAll());

  fastify.post('/automations', {
    preHandler: [verifyJwt],
    schema: {
      tags: ['Automation'],
      summary: 'Criar automação',
      security: [{ bearerAuth: [] }],
      body: {
        type: 'object',
        required: ['name', 'funnelId', 'triggers', 'actions'],
        properties: {
          name: { type: 'string' },
          description: { type: 'string' },
          funnelId: { type: 'number' },
          triggers: { type: 'object' },
          actions: { type: 'object' }
        }
      },
      response: {
        201: {
          type: 'object',
          properties: {
            id: { type: 'number' },
            name: { type: 'string' },
            description: { type: 'string' },
            funnelId: { type: 'number' },
            triggers: { type: 'object' },
            actions: { type: 'object' },
            createdAt: { type: 'string', format: 'date-time' },
            updatedAt: { type: 'string', format: 'date-time' }
          }
        }
      }
    }
  }, async (request, reply) => {
    const { name, description, funnelId, triggers, actions } = request.body as any;
    const automation = await AutomationRepository.create({ name, description, funnelId, triggers, actions });
    reply.code(201);
    return automation;
  });

  fastify.put('/automations/:id', {
    preHandler: [verifyJwt],
    schema: {
      tags: ['Automation'],
      summary: 'Atualizar automação',
      security: [{ bearerAuth: [] }],
      params: {
        type: 'object',
        properties: { id: { type: 'integer' } },
        required: ['id']
      },
      body: {
        type: 'object',
        properties: {
          name: { type: 'string' },
          description: { type: 'string' },
          triggers: { type: 'object' },
          actions: { type: 'object' }
        }
      },
      response: {
        200: {
          type: 'object',
          properties: {
            id: { type: 'number' },
            name: { type: 'string' },
            description: { type: 'string' },
            funnelId: { type: 'number' },
            triggers: { type: 'object' },
            actions: { type: 'object' },
            createdAt: { type: 'string', format: 'date-time' },
            updatedAt: { type: 'string', format: 'date-time' }
          }
        }
      }
    }
  }, async (request, reply) => {
    const id = Number((request.params as any).id);
    const { name, description, triggers, actions } = request.body as any;
    const automation = await AutomationRepository.update(id, { name, description, triggers, actions });
    return automation;
  });

  fastify.delete('/automations/:id', {
    preHandler: [verifyJwt],
    schema: {
      tags: ['Automation'],
      summary: 'Remover automação',
      security: [{ bearerAuth: [] }],
      params: {
        type: 'object',
        properties: { id: { type: 'integer' } },
        required: ['id']
      },
      response: { 204: { type: 'null' } }
    }
  }, async (request, reply) => {
    const id = Number((request.params as any).id);
    await AutomationRepository.delete(id);
    reply.code(204).send();
  });
}