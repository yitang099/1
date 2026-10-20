import { readAuth, ok, err } from '../../utils/api'
import {
  createJob,
  deleteJob,
  getJob,
  getTemplate,
  guestSignUp,
  listFavorites,
  listJobs,
  listTemplates,
  resolveUser,
  setFavorite,
} from '../../utils/store'

export default defineEventHandler(async (event) => {
  const pathParam = event.context.params?.path
  const rpc = Array.isArray(pathParam) ? pathParam.join('.') : String(pathParam || '')
  const method = event.method

  if (rpc === 'user-guest.sign-up' && method === 'POST') {
    const body = await readBody<{ gender?: string }>(event)
    const gender = String(body?.gender || '').trim()
    if (!gender) return err(10002, 'invalid gender')
    const { user, access_token } = guestSignUp(gender)
    return ok({
      auth: { access_token, token_type: 'Bearer', expires: 604800 },
      user,
    })
  }

  if (rpc === 'user.whoami' && method === 'GET') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    return ok({ user })
  }

  if (rpc === 'generation-template.list' && method === 'GET') {
    const q = getQuery(event)
    const user = resolveUser(readAuth(event))
    return ok(
      listTemplates({
        page: Number(q.page || 1),
        page_size: Number(q.page_size || 20),
        q: String(q.q || ''),
        user_id: user?.uuid,
      }),
    )
  }

  if (rpc === 'generation-template.recommend-list' && method === 'GET') {
    const q = getQuery(event)
    return ok(
      listTemplates({
        page: Number(q.page || 1),
        page_size: Number(q.page_size || 20),
      }),
    )
  }

  if (rpc === 'generation-template-favorite.list' && method === 'GET') {
    const user = resolveUser(readAuth(event))
    if (!user) return err(10022, 'unauthorized')
    const favIds = new Set(listFavorites(user.uuid))
    const items = listTemplates({ page: 1, page_size: 100 }).items.filter((t) =>
      favIds.has(t.id),
    )
    return ok({ items })
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
        e && typeof e === 'object' && 'statusMessage' in e
          ? String((e as { statusMessage?: string }).statusMessage)
          : 'error'
      return err(10001, msg)
    }
  }

  if (rpc === 'user-generation-content.get' && method === 'GET') {
    // Genspicy-style RPC name (includes ".get")
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
    const tpl =
      getTemplate(id) ||
      listTemplates({ page: 1, page_size: 500 }).items.find((t) => t.slug === id)
    if (!tpl) return err(10001, 'not found')
    const user = resolveUser(readAuth(event))
    const is_favorited = user
      ? listFavorites(user.uuid).includes(tpl.id)
      : false
    return ok({ item: { ...tpl, is_favorited } })
  }

  throw createError({ statusCode: 404, statusMessage: 'Page not found' })
})
