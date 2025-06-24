import { PrismaClient } from '@prisma/client';
const prisma = new PrismaClient();

export const UserRepository = {
  findAll: () => prisma.user.findMany(),
  findById: (id: number) => prisma.user.findUnique({ where: { id } }),
  create: (data: { email: string; name: string }) => prisma.user.create({ data }),
  update: (id: number, data: { email?: string; name?: string }) =>
    prisma.user.update({ where: { id }, data }),
  delete: (id: number) => prisma.user.delete({ where: { id } }),
};