import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

export const AutomationRepository = {
  findAll: () => prisma.automation.findMany({ include: { funnel: true } }),
  findById: (id: number) => prisma.automation.findUnique({ where: { id }, include: { funnel: true } }),
  create: (data: { name: string; description?: string; funnelId: number; triggers: any; actions: any }) =>
    prisma.automation.create({ data }),
  update: (id: number, data: { name?: string; description?: string; triggers?: any; actions?: any }) =>
    prisma.automation.update({ where: { id }, data }),
  delete: (id: number) => prisma.automation.delete({ where: { id } }),
};