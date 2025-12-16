import { supabase } from '../lib/supabase';

export async function logAudit(
  action: string,
  resourceType: string,
  resourceId?: string,
  details?: Record<string, unknown>
) {
  try {
    const { data: { user } } = await supabase.auth.getUser();

    await supabase.from('audit_logs').insert({
      user_id: user?.id || null,
      action,
      resource_type: resourceType,
      resource_id: resourceId || null,
      details: details || {},
    });
  } catch (error) {
    console.error('Failed to log audit:', error);
  }
}
