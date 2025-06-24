import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

export const FunnelRepository = {
  findAll: () => prisma.funnel.findMany(),
  findById: (id: number) => prisma.funnel.findUnique({ where: { id } }),
  create: (data: { name: string; description?: string }) => prisma.funnel.create({ data }),
  update: (id: number, data: { name?: string; description?: string }) =>
    prisma.funnel.update({ where: { id }, data }),
  delete: (id: number) => prisma.funnel.delete({ where: { id } }),
};