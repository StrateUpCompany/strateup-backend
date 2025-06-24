import { FastifyRequest, FastifyReply } from 'fastify';
import jwt from 'jsonwebtoken';

export async function verifyJwt(request: FastifyRequest, reply: FastifyReply) {
  try {
    const authHeader = request.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      reply.status(401).send({ error: 'Missing or invalid Authorization header' });
      return;
    }

    const token = authHeader.replace('Bearer ', '').trim();
    const secret = process.env.SUPABASE_JWT_SECRET as string;
    const decoded = jwt.verify(token, secret);
    (request as any).user = decoded;
  } catch (err) {
    reply.status(401).send({ error: 'Unauthorized' });
  }
}