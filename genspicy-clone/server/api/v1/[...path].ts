import { readAuth, ok, err } from '../../utils/api'
import {
  affiliateClick,
  affiliateStats,
  createJob,
  deleteJob,
  extendJob,
  getJob,
  getTemplate,
  grantDiamonds,
  guestSignUp,
  listFavoriteTemplates,
  listFavorites,
  listJobs,
  listTemplates,
  memberSignInOrSignUp,
  resolveUser,
  setFavorite,
  setJobLike,
  updateUserProfile,
} from '../../utils/store'
import { catalogSize } from '../../utils/catalog'

export default defineEventHandler(async (event) => {
  const pathParam = event.context.params?.path
  const rpc = Array.isArray(pathParam) ? pathParam.join('.') : String(pathParam || '')
  const method = event.method

  if (rpc === 'user-guest.sign-up' && method === 'POST') {
    const body = await readBody<{ gender?: string; referred_by?: string }>(event)
    const gender = String(body?.gender || '').trim()
    if (!gender) return err(10002, 'invalid gender')
    const { user, access_token } = guestSignUp(gender, body?.referred_by)
    return ok({
      auth: { access_token, token_type: 'Bearer', expires: 604800 },
      user,
    })
  }

  if (rpc === 'user.sign-in-or-sign-up' && method === 'POST') {
    try {
      const body = await readBody<{
        email?: string
        gender?: string
        name?: string
        referred_by?: string
      }>(event)
      const { user, access_token } = memberSignInOrSignUp(body || {})
      return ok({
        auth: { access_token, token_type: 'Bearer', expires: 604800 },
        user,
      })
    } catch (e: unknown) {
      const msg = e && typeof e === 'object' && 'message' in e ? String((e as { message?: string }).message) : 'error'
      return err(10002, msg)
    }
  }

  if (rpc === 'user.whoami' && method === 'GET') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    return ok({ user })
  }

  if (rpc === 'user.profile.update' && method === 'POST') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    const body = await readBody<{ name?: string; photo_url?: string }>(event)
    const updated = updateUserProfile(user.uuid, body || {})
    return ok({ user: updated })
  }

  if (rpc === 'app.config.get' && method === 'GET') {
    return ok({
      site_name: 'Genspicy Clone',
      payment_enabled: false,
      template_count: catalogSize(),
      features: ['explore', 'drama', 'tools', 'affiliate', 'extend', 'favorites'],
    })
  }

  if (rpc === 'generation-template.list' && method === 'GET') {
    const q = getQuery(event)
    const user = resolveUser(readAuth(event))
    return ok(
      listTemplates({
        page: Number(q.page || 1),
        page_size: Number(q.page_size || 20),
        q: String(q.q || ''),
        tag: String(q.tag || ''),
        display_scene: String(q.display_scene || ''),
        generate_mode: String(q.generate_mode || ''),
        template_type: String(q.template_type || ''),
        user_id: user?.uuid,
      }),
    )
  }

  if (rpc === 'generation-template.recommend-list' && method === 'GET') {
    const q = getQuery(event)
    const user = resolveUser(readAuth(event))
    return ok(
      listTemplates({
        page: Number(q.page || 1),
        page_size: Number(q.page_size || 20),
        recommend: true,
        user_id: user?.uuid,
      }),
    )
  }

  if (rpc === 'generation-template-favorite.list' && method === 'GET') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    const q = getQuery(event)
    return ok(
      listFavoriteTemplates(
        user.uuid,
        Number(q.page || 1),
        Number(q.page_size || 20),
      ),
    )
  }

  if (rpc === 'generation-template-favorite.toggle' && method === 'POST') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    const body = await readBody<{ template_id?: string; favorited?: boolean }>(event)
    if (!body?.template_id) return err(10001, 'bad request')
    setFavorite(user.uuid, body.template_id, Boolean(body.favorited))
    return ok({ favorited: Boolean(body.favorited) })
  }

  if (rpc === 'user-generation-content.create' && method === 'POST') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    const body = await readBody<{
      template_id?: string
      input_url?: string
      features?: string[]
    }>(event)
    if (!body?.template_id) return err(10001, 'bad request')
    try {
      const job = createJob({
        user,
        template_id: body.template_id,
        input_url: body.input_url,
        features: body.features || [],
      })
      return ok({ item: job })
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'error'
      return err(10001, msg)
    }
  }

  if (rpc === 'user-generation-content.extend' && method === 'POST') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    const body = await readBody<{ id?: string }>(event)
    if (!body?.id) return err(10001, 'bad request')
    try {
      const job = extendJob(body.id, user.uuid)
      if (!job) return err(10022, 'unauthorized')
      return ok({ item: job })
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'message' in e
          ? String((e as { message?: string }).message)
          : 'error'
      return err(10001, msg)
    }
  }

  if (rpc === 'user-generation-content.like-status.update' && method === 'POST') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    const body = await readBody<{ id?: string; liked?: boolean }>(event)
    if (!body?.id) return err(10001, 'bad request')
    const job = setJobLike(body.id, user.uuid, Boolean(body.liked))
    if (!job) return err(10022, 'unauthorized')
    return ok({ item: job })
  }

  if (rpc === 'user-generation-content.get' && method === 'GET') {
    const user = resolveUser(readAuth(event))
    const id = String(getQuery(event).id || '')
    if (!id) return err(10001, 'bad request')
    const job = getJob(id, user?.uuid)
    if (!job) return err(10022, 'unauthorized')
    return ok({ item: job })
  }

  if (rpc === 'user-generation-content.list' && method === 'GET') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    const q = getQuery(event)
    return ok(listJobs(user.uuid, Number(q.page || 1), Number(q.page_size || 20)))
  }

  if (rpc === 'user-generation-content.delete' && method === 'POST') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    const body = await readBody<{ id?: string }>(event)
    if (!body?.id) return err(10001, 'bad request')
    if (!deleteJob(body.id, user.uuid)) return err(10022, 'unauthorized')
    return ok({ deleted: true })
  }

  if (rpc === 'generation-template.get' && method === 'GET') {
    const id = String(getQuery(event).id || getQuery(event).slug || '')
    const tpl = getTemplate(id)
    if (!tpl) return err(10001, 'not found')
    const user = resolveUser(readAuth(event))
    const is_favorited = user ? listFavorites(user.uuid).includes(tpl.id) : false
    return ok({ item: { ...tpl, is_favorited } })
  }

  if (rpc === 'affiliate.stats.get' && method === 'GET') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    const code = user.referral_code || user.uuid.slice(0, 8)
    const stats = affiliateStats(code)
    return ok({
      referral_code: code,
      signups: stats.signups,
      clicks: stats.clicks,
      earnings_usd: 0,
      payout_enabled: false,
    })
  }

  if (rpc === 'affiliate.click.track' && method === 'POST') {
    const body = await readBody<{ referral_code?: string }>(event)
    const code = String(body?.referral_code || '').trim()
    if (!code) return err(10001, 'bad request')
    return ok({ stats: affiliateClick(code) })
  }

  if (rpc === 'wallet.diamonds.grant-demo' && method === 'POST') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    const updated = grantDiamonds(user.uuid, 200)
    return ok({ user: updated, note: 'Local demo grant — no payment' })
  }

  throw createError({ statusCode: 404, statusMessage: 'Page not found' })
})
