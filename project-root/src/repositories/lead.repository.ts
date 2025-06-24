import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

export const LeadRepository = {
  findAll: () => prisma.lead.findMany({ include: { funnel: true, owner: true } }),
  findById: (id: number) => prisma.lead.findUnique({ where: { id }, include: { funnel: true, owner: true } }),
  create: (data: { name: string; email: string; funnelId: number; ownerId: number }) =>
    prisma.lead.create({ data }),
  update: (id: number, data: { name?: string; email?: string; funnelId?: number }) =>
    prisma.lead.update({ where: { id }, data }),
  delete: (id: number) => prisma.lead.delete({ where: { id } }),
};