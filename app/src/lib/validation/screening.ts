import { z } from 'zod';

const optionalNumber = (schema: z.ZodNumber) =>
  z.preprocess(
    (v) => (v === '' || v === null || Number.isNaN(v) ? undefined : v),
    schema.optional()
  );

export const screeningSchema = z
  .object({
    // Step 1 — glucose
    glucose_mg_dl: optionalNumber(z.number().min(0).max(1000)),
    glucose_type: z
      .enum(['fasting', 'postprandial', 'random', 'hba1c', 'ogtt'])
      .default('fasting'),

    // Step 2 — vitals & lipids
    sbp: optionalNumber(z.number().int().min(0).max(300)),
    dbp: optionalNumber(z.number().int().min(0).max(200)),
    height_cm: optionalNumber(z.number().min(30).max(300)),
    weight_kg: optionalNumber(z.number().min(1).max(500)),
    ldl_mg_dl: optionalNumber(z.number().min(0).max(500)),
    hdl_mg_dl: optionalNumber(z.number().min(0).max(200)),
    triglycerides_mg_dl: optionalNumber(z.number().min(0).max(2000)),

    // Step 3 — demographics & history
    age: optionalNumber(z.number().int().min(0).max(150)),
    sex: z.enum(['M', 'F']).optional(),
    family_history: z.boolean().default(false),
    medications: z.array(z.string()).default([]),
    comorbidities: z.array(z.string()).default([]),
    pregnancy_status: z.enum(['none', 'gestational', 'preexisting']).optional(),
    unit_preference: z.enum(['mg_dL', 'mmol_L']).default('mg_dL'),
  })
  .refine(
    (d) => !(d.sbp != null && d.dbp != null && d.dbp >= d.sbp),
    { message: 'Diastolic pressure must be less than systolic', path: ['dbp'] }
  );

export type ScreeningFormValues = z.infer<typeof screeningSchema>;

export const stepFields: Record<number, (keyof ScreeningFormValues)[]> = {
  0: ['glucose_mg_dl', 'glucose_type'],
  1: ['sbp', 'dbp', 'height_cm', 'weight_kg', 'ldl_mg_dl', 'hdl_mg_dl', 'triglycerides_mg_dl'],
  2: ['age', 'sex', 'family_history'],
};
