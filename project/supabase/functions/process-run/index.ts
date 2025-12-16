import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.57.4";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Client-Info, Apikey",
};

Deno.serve(async (req: Request) => {
  const origin = req.headers.get("Origin") || "*";
  const cors = { ...corsHeaders, "Access-Control-Allow-Origin": origin };
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 200, headers: cors });
  }

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL")!;
    const supabaseServiceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;

    const authHeader = req.headers.get("Authorization") || "";
    if (!authHeader) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401, headers: { ...cors, "Content-Type": "application/json" } });
    }

    // Use service role for DB writes, but pass through user Authorization for identity
    const supabase = createClient(supabaseUrl, supabaseServiceKey, {
      global: { headers: { Authorization: authHeader } },
    });

    const { data: { user }, error: authError } = await supabase.auth.getUser();
    if (authError || !user) {
      return new Response(JSON.stringify({ error: "Unauthorized" }), { status: 401, headers: { ...cors, "Content-Type": "application/json" } });
    }

    // Role check
    const { data: userProfile, error: profileError } = await supabase
      .from("user_profiles")
      .select("role")
      .eq("id", user.id)
      .single();
    if (profileError || !userProfile || (userProfile.role !== "admin" && userProfile.role !== "technical_writer")) {
      return new Response(JSON.stringify({ error: "Forbidden" }), { status: 403, headers: { ...cors, "Content-Type": "application/json" } });
    }

    const { runId } = await req.json();
    if (!runId) {
      return new Response(JSON.stringify({ error: "runId is required" }), { status: 400, headers: { ...cors, "Content-Type": "application/json" } });
    }

    // Update run status to 'processing'
    await supabase
      .from("runs")
      .update({ status: "processing" })
      .eq("id", runId);

    // Instead of simulating here, the actual processing will be done by the Python worker.
    // This Edge Function now acts as a lightweight dispatcher.

    return new Response(JSON.stringify({
      success: true,
      message: "Run status updated to processing. Worker will pick it up.",
      runId: runId,
    }), { headers: { ...cors, "Content-Type": "application/json" } });
  } catch (error) {
    console.error("Error in process-run function:", error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : "Unknown error" }), { status: 500, headers: { ...cors, "Content-Type": "application/json" } });
  }
});
