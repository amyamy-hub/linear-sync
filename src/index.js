export default {
  async fetch(request) {
    const { pathname } = new URL(request.url);

    if (pathname === "/health") {
      return Response.json({ ok: true, service: "linear-sync" });
    }

    return Response.json(
      { error: "not_implemented", endpoints: ["/health"] },
      { status: 501 }
    );
  },
};
