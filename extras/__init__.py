"""CareerSathi Growth Pack (v11) + Launch Pack (v12). Hooked from app.py with:
    from extras import router; app.include_router(router); from extras import promote_overrides; promote_overrides(app)"""
import os
from jinja2 import pass_context
from starlette.middleware import Middleware
from .routes import router  # noqa: F401
from .routes2 import router as _r2, V12Middleware, login_guarded, journey_gate, journey_enquiry_guarded, journey_assessment_guarded
from .routes3 import router as _r3, start_scheduler
from .routes4 import router as _r4, approved_stories
from . import services as S
from .data2 import HI

for _r in (_r2, _r3, _r4): router.include_router(_r)

def _asset_version():
    """Changes whenever a static file changes, so browsers never keep serving an old stylesheet or script."""
    import hashlib, glob
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    h = hashlib.md5()
    for f in sorted(glob.glob(os.path.join(base, 'static', '*.css')) + glob.glob(os.path.join(base, 'static', '*.js'))): h.update(('%s%s' % (os.path.basename(f), os.path.getmtime(f))).encode())
    return h.hexdigest()[:8]

@pass_context
def t(ctx, text):
    """Hindi labels for navigation and v12 pages when the 'lang' cookie is 'hi'."""
    req = ctx.get('request')
    return HI.get(text, text) if req is not None and req.cookies.get('lang') == 'hi' else text


_TITLES = {400: ('Please check and try again', '📝'), 401: ('Please log in', '🔐'), 403: ('You do not have access', '🚫'), 404: ('Page not found', '🧭'),
           409: ('That is already taken', '⚠️'), 429: ('Too many attempts', '⏳')}

async def _friendly_errors(request, exc):
    """Browsers get a readable page instead of raw JSON like {"detail": "..."}; API clients and tests (no text/html in Accept) still get JSON."""
    from starlette.responses import RedirectResponse
    from fastapi.exception_handlers import http_exception_handler
    code = exc.status_code; path = request.url.path
    if code >= 400 and 'text/html' in request.headers.get('accept', '') and not path.startswith(('/api', '/static', '/assistant/ask', '/pay/webhook', '/pay/verify')):
        import app as core
        if code == 401 and request.method == 'GET' and path != '/login':
            core.notice(request, 'Please log in to continue.'); return RedirectResponse('/login', 303)
        heading, icon = _TITLES.get(code, ('Something went wrong', '⚠️'))
        resp = core.render(request, 'x_error.html', code=code, heading=heading, icon=icon, message=str(exc.detail) if isinstance(exc.detail, str) else heading)
        resp.status_code = code
        return resp
    return await http_exception_handler(request, exc)

def promote_overrides(app):
    import app as core
    core.SessionLocal.configure(expire_on_commit=False)   # fixes legacy routes that read `user.role` after the session closed (e.g. booking confirm)
    from starlette.exceptions import HTTPException as _SHTTP
    app.add_exception_handler(_SHTTP, _friendly_errors)
    app.user_middleware.append(Middleware(V12Middleware))       # innermost: runs after SessionMiddleware
    core.tpl.env.globals.update(asset_v=_asset_version(), t=t, x_stories=approved_stories, x_site_key=lambda: S.env('TURNSTILE_SITE_KEY') if S.captcha_enabled() else '')
    # Override /login (throttle + CAPTCHA) and /journey (onboarding gate). Routes are built directly and put FIRST so they win,
    # whichever FastAPI version flattens or mounts included routers.
    from fastapi.routing import APIRoute
    app.router.routes[0:0] = [APIRoute('/login', login_guarded, methods=['POST']), APIRoute('/journey', journey_gate, methods=['GET']),
                              APIRoute('/journey/enquiry', journey_enquiry_guarded, methods=['POST']), APIRoute('/journey/assessment', journey_assessment_guarded, methods=['POST'])]
    from contextlib import asynccontextmanager
    _orig = app.router.lifespan_context
    @asynccontextmanager
    async def _lifespan(a):
        start_scheduler()                      # background reminders + parent digests
        async with _orig(a) as state: yield state
    app.router.lifespan_context = _lifespan
    if os.getenv('SENTRY_DSN'):
        try:
            import sentry_sdk; sentry_sdk.init(dsn=os.getenv('SENTRY_DSN'), traces_sample_rate=0.05, send_default_pii=False)
        except Exception as e: S.log.warning('Sentry not started: %s', e)
