import { z } from 'zod';
export const registration = z.object({label:z.string().trim().min(1,'Escribe una etiqueta').max(120),grace_days:z.coerce.number().int().min(0).max(31)});
export const payment = z.object({until:z.string().regex(/^\d{4}-\d{2}-\d{2}$/,'Selecciona la fecha pagada')});
export const pause = z.object({reason:z.string().trim().min(1,'Escribe el motivo').max(200)});
export const reportPeriod = z.object({start_date:z.iso.date(),end_date:z.iso.date()}).refine(v=>v.start_date<=v.end_date,{message:'La fecha inicial debe ir antes de la final'});
