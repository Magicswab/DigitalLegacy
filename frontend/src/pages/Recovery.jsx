import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import { useToast, Card, CardTitle, PageHeader, Empty, Btn, Field, Select, LogBox, useLog } from '../components/UI'
import { getMyPackages, getMyPlans, getRecoverySession, getPlanRecoverySessions, getAssetEncryptedBlob } from '../api'

// ── 암호화 유틸 ──────────────────────────────────────────
const b64ToBytes = (b64) => Uint8Array.from(atob(b64), c => c.charCodeAt(0))

const decryptPackage = async (encryptedBlobJson, privateKeyPem) => {
  const payload = JSON.parse(encryptedBlobJson)
  const pemBody = privateKeyPem
    .replace(/-----BEGIN PRIVATE KEY-----/, '')
    .replace(/-----END PRIVATE KEY-----/, '')
    .replace(/\s/g, '')
  const privateKey = await crypto.subtle.importKey(
    'pkcs8', b64ToBytes(pemBody).buffer,
    { name: 'RSA-OAEP', hash: 'SHA-256' }, false, ['decrypt']
  )
  const aesKeyBytes = await crypto.subtle.decrypt(
    { name: 'RSA-OAEP' }, privateKey, b64ToBytes(payload.encrypted_key)
  )
  const aesKey = await crypto.subtle.importKey(
    'raw', aesKeyBytes, { name: 'AES-GCM' }, false, ['decrypt']
  )
  const plaintext = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: b64ToBytes(payload.nonce) },
    aesKey, b64ToBytes(payload.ciphertext)
  )
  return JSON.parse(new TextDecoder().decode(plaintext))
}

// DEK + nonce로 암호화된 blob 복호화
const decryptAssetBlob = async (encryptedB64, dekB64, nonceB64) => {
  const key = await crypto.subtle.importKey(
    'raw', b64ToBytes(dekB64), { name: 'AES-GCM' }, false, ['decrypt']
  )
  const plaintext = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: b64ToBytes(nonceB64) },
    key, b64ToBytes(encryptedB64)
  )
  return new Uint8Array(plaintext)
}

const downloadBlob = (bytes, filename, mimeType) => {
  const blob = new Blob([bytes], { type: mimeType || 'application/octet-stream' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

// ── 상수 ──────────────────────────────────────────────────
const MIME_ICON = {
  'application/pdf': '📄', 'video/mp4': '🎬', 'video/quicktime': '🎬',
  'image/jpeg': '🖼', 'image/png': '🖼', 'audio/mpeg': '🎵',
  'text/plain': '📝', 'application/msword': '📋',
}
const TYPE_COLOR = { credential: 'var(--accent)', document: 'var(--cyan)', media: 'var(--amber)' }

export default function Recovery() {
  const { user } = useAuth()
  const toast = useToast()
  const { lines, add } = useLog()

  const [plans, setPlans]               = useState([])
  const [planId, setPlanId]             = useState('')
  const [sessions, setSessions]         = useState([])
  const [sessLoading, setSessL]         = useState(false)
  const [selectedSessionId, setSelSess] = useState('')
  const [sessionInfo, setSessionInfo]   = useState(null)

  const [packages, setPackages]         = useState([])
  const [pkgLoading, setPkgL]           = useState(false)
  const [privateKeyPem, setPrivKeyPem]  = useState('')
  const [decryptedPkg, setDecryptedPkg] = useState(null)
  const [decLoading, setDecL]           = useState(false)

  // 자산별 다운로드 상태
  const [downloadingId, setDownloadingId] = useState(null)

  useEffect(() => {
    getMyPlans(user.user_id).then(r => setPlans(r.data.plans || r.data || [])).catch(() => {})
    loadPackages()
  }, [])

  useEffect(() => {
    if (!planId) { setSessions([]); setSelSess(''); setSessionInfo(null); return }
    loadSessions(planId)
  }, [planId])

  useEffect(() => {
    if (!selectedSessionId) { setSessionInfo(null); return }
    handleCheckSession(selectedSessionId)
  }, [selectedSessionId])

  const loadSessions = async (pid) => {
    setSessL(true)
    try {
      const r = await getPlanRecoverySessions(pid)
      const list = r.data.sessions || []
      setSessions(list)
      add(`${list.length}개 recovery session 확인됨`, 'ok')
      const completed = list.find(s => s.status === 'completed')
      if (completed) setSelSess(completed.recovery_id)
    } catch { setSessions([]) }
    finally { setSessL(false) }
  }

  const loadPackages = async () => {
    setPkgL(true)
    add(`GET /users/${user.user_id}/packages`, 'info')
    try {
      const r = await getMyPackages(user.user_id)
      const list = r.data.packages || []
      setPackages(list)
      add(`${list.length}개 패키지 확인됨`, 'ok')
    } catch (e) { add(`오류: ${e.response?.data?.detail || e.message}`, 'err') }
    finally { setPkgL(false) }
  }

  const handleCheckSession = async (id) => {
    try {
      const r = await getRecoverySession(id)
      setSessionInfo(r.data)
      add(`세션 상태: ${r.data.status} | 제출: ${r.data.submissions?.length || 0}/${r.data.threshold_required}`, 'ok')
    } catch (e) { add(`오류: ${e.response?.data?.detail || e.message}`, 'err') }
  }

  // 패키지 복호화 (개인키로 vault 열기)
  const handleDecryptPackage = async (pkg) => {
    if (!privateKeyPem.trim()) { toast('개인키를 입력하세요', 'err'); return }
    if (!pkg.encrypted_package_blob) {
      toast('패키지 blob 없음 — 백엔드를 재시작하고 다시 로드해주세요', 'err')
      return
    }
    setDecL(true)
    add(`패키지 복호화 중: ${pkg.package_id}`, 'info')
    try {
      const result = await decryptPackage(pkg.encrypted_package_blob, privateKeyPem)
      setDecryptedPkg({ ...result, package_id: pkg.package_id })
      add(`vault 복호화 성공 — 자산 ${result.vault_contents?.assets?.length || 0}개`, 'ok')
      toast('패키지 복호화 성공! 아래에서 자산을 다운로드하세요.', 'ok')
    } catch (e) {
      if (e.name === 'OperationError') {
        toast('복호화 실패 — 올바른 beneficiary 개인키인지 확인하세요', 'err')
        add('오류: 개인키가 이 패키지 수신자 키와 다릅니다', 'err')
      } else if (e.name === 'DataError') {
        toast('키 형식 오류 — PEM 전체를 정확히 붙여넣었는지 확인하세요', 'err')
        add(`오류: ${e.message}`, 'err')
      } else {
        toast('복호화 실패: ' + e.message, 'err')
        add(`오류: ${e.message}`, 'err')
      }
    } finally { setDecL(false) }
  }

  // 개별 자산 복호화 + 다운로드 (브라우저에서만)
  const handleDownloadAsset = async (assetMeta) => {
    const { asset_id, dek, nonce } = assetMeta
    // vault에 없을 수 있는 필드는 옵셔널로 처리
    const asset_name = assetMeta.asset_name || null
    const vault_mime = assetMeta.mime_type || null

    if (!dek || !nonce) { toast('DEK 또는 nonce가 vault에 없습니다', 'err'); return }

    setDownloadingId(asset_id)
    add(`암호화 파일 요청 중: ${asset_name || asset_id}`, 'info')
    try {
      // 1. 백엔드에서 암호화된 .bin 파일 + 메타 가져오기
      const r = await getAssetEncryptedBlob(asset_id)
      const encryptedB64 = r.data.encrypted_blob
      // vault에 mime/name 없으면 백엔드 assets 테이블 값으로 폴백
      const mime_type = vault_mime || r.data.mime_type || 'application/octet-stream'
      const name      = asset_name || r.data.asset_name || asset_id
      add(`암호화 파일 수신 완료 (${r.data.encrypted_size}B) | MIME: ${mime_type}`, 'ok')

      // 2. 브라우저에서 DEK + nonce로 복호화
      add(`브라우저 복호화 중...`, 'info')
      const decryptedBytes = await decryptAssetBlob(encryptedB64, dek, nonce)

      // 3. 파일명 결정
      const EXT = {
        'text/plain': '.txt', 'application/pdf': '.pdf',
        'image/jpeg': '.jpg', 'image/png': '.png',
        'video/mp4': '.mp4', 'audio/mpeg': '.mp3',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
      }
      const ext = EXT[mime_type] || ''
      const filename = (name && name.includes('.')) ? name : `${name}${ext}`

      // 4. 다운로드
      downloadBlob(decryptedBytes, filename, mime_type)
      add(`✅ 다운로드 완료: ${filename} (${decryptedBytes.length}B)`, 'ok')
      toast(`${filename} 다운로드 완료!`, 'ok')
    } catch (e) {
      toast('다운로드 실패: ' + e.message, 'err')
      add(`오류: ${e.message}`, 'err')
    } finally { setDownloadingId(null) }
  }

  return (
    <div style={{ padding: '24px 28px', animation: 'fadeUp 0.3s ease' }}>
      <PageHeader title="자산 복구" sub="패키지 복호화 · 클라이언트 사이드 · 개인키 미전송" />

      {/* 복구 흐름 */}
      <Card style={{ borderColor: 'rgba(74,184,212,0.2)', background: 'rgba(74,184,212,0.03)' }}>
        <CardTitle>복구 프로토콜</CardTitle>
        <div style={{ display: 'flex', alignItems: 'center' }}>
          {['① Share 제출', '② 임계값 충족', '③ 패키지 생성', '④ 개인키 입력', '⑤ 복호화', '⑥ 파일 다운로드'].map((step, i, arr) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', flex: i < arr.length - 1 ? 1 : 'auto' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--cyan)', textAlign: 'center', whiteSpace: 'nowrap' }}>{step}</div>
              {i < arr.length - 1 && <div style={{ flex: 1, height: 1, background: 'var(--border)', margin: '0 6px' }} />}
            </div>
          ))}
        </div>
      </Card>

      {/* 플랜 + 세션 선택 */}
      <Card>
        <CardTitle>플랜 및 Recovery Session 선택</CardTitle>
        <Field label="플랜 선택">
          <Select value={planId} onChange={e => setPlanId(e.target.value)}>
            <option value="">— 플랜을 선택하세요 —</option>
            {plans.map(p => (
              <option key={p.plan_id} value={p.plan_id}>{p.title} ({p.status})</option>
            ))}
          </Select>
        </Field>

        {planId && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <label style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase', color: 'var(--text2)' }}>Recovery Session</label>
              <Btn v="ghost" sm onClick={() => loadSessions(planId)} loading={sessLoading}>새로고침</Btn>
            </div>
            {sessions.length === 0 ? (
              <div style={{ fontSize: 12, color: 'var(--text3)', fontFamily: 'var(--mono)', padding: '10px 0' }}>생성된 Recovery Session이 없습니다</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {sessions.map((s, i) => {
                  const rid = s.recovery_id || ''
                  const isSelected = selectedSessionId === rid
                  return (
                    <div key={i} onClick={() => setSelSess(isSelected ? '' : rid)} style={{
                      padding: '10px 13px', cursor: 'pointer',
                      background: isSelected ? 'var(--accent-d)' : 'var(--surface2)',
                      border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                      borderRadius: 'var(--r-sm)', transition: 'all .15s',
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ fontFamily: 'var(--mono)', fontSize: 11, color: 'var(--text)' }}>{rid.slice(0, 36)}...</div>
                        <span style={{
                          fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
                          background: s.status === 'completed' ? 'var(--green-d)' : 'var(--amber-d)',
                          color: s.status === 'completed' ? 'var(--green)' : 'var(--amber)',
                          textTransform: 'uppercase',
                        }}>{s.status || 'open'}</span>
                      </div>
                      {s.created_at && <div style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 3 }}>{new Date(s.created_at).toLocaleString('ko-KR')}</div>}
                    </div>
                  )
                })}
              </div>
            )}

            {/* 세션 진행 상태 */}
            {sessionInfo && (
              <div style={{ marginTop: 14, padding: '12px 14px', background: 'var(--surface2)', border: '1px solid var(--border)', borderRadius: 'var(--r-sm)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text2)' }}>세션 상태</span>
                  <span style={{ fontSize: 11, fontWeight: 700, fontFamily: 'var(--mono)', color: sessionInfo.status === 'completed' ? 'var(--green)' : 'var(--amber)' }}>
                    {sessionInfo.status?.toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--text3)', marginBottom: 5 }}>
                  임계값 진행: {sessionInfo.submissions?.length || 0} / {sessionInfo.threshold_required}
                </div>
                <div style={{ height: 4, background: 'var(--border)', borderRadius: 2 }}>
                  <div style={{
                    height: '100%',
                    width: `${Math.min(100, ((sessionInfo.submissions?.length || 0) / sessionInfo.threshold_required) * 100)}%`,
                    background: sessionInfo.status === 'completed' ? 'var(--green)' : 'var(--cyan)',
                    borderRadius: 2, transition: 'width 0.4s',
                    boxShadow: sessionInfo.status === 'completed' ? '0 0 6px var(--green)' : 'none',
                  }} />
                </div>
              </div>
            )}
          </>
        )}
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {/* 패키지 목록 */}
        <Card>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <CardTitle>내 패키지</CardTitle>
            <Btn v="ghost" sm onClick={loadPackages} loading={pkgLoading}>새로고침</Btn>
          </div>

          <Field label="개인키 (PEM)">
            <textarea
              placeholder="-----BEGIN PRIVATE KEY-----&#10;...&#10;-----END PRIVATE KEY-----"
              value={privateKeyPem}
              onChange={e => setPrivKeyPem(e.target.value)}
              style={{
                background: 'var(--surface2)', border: '1px solid var(--border)',
                borderRadius: 'var(--r-sm)', color: 'var(--amber)',
                fontFamily: 'var(--mono)', fontSize: 10,
                padding: '8px 10px', width: '100%', outline: 'none',
                resize: 'vertical', minHeight: 70, lineHeight: 1.5,
              }}
            />
            <div style={{ fontSize: 10, color: 'var(--text3)', fontFamily: 'var(--mono)', marginTop: 3 }}>
              // 키는 브라우저에서만 사용 — 서버로 전송되지 않습니다
            </div>
          </Field>

          {packages.length === 0 ? (
            <Empty msg="수신된 패키지가 없습니다 (상속 활성화 후 생성됩니다)" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {packages.map((pkg, i) => (
                <div key={i} style={{
                  background: decryptedPkg?.package_id === pkg.package_id ? 'var(--green-d)' : 'var(--surface2)',
                  border: `1px solid ${decryptedPkg?.package_id === pkg.package_id ? 'var(--green)' : 'var(--border)'}`,
                  borderRadius: 'var(--r-sm)', padding: 12,
                  borderLeft: '2px solid var(--cyan)', transition: 'all .2s',
                }}>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--cyan)', marginBottom: 6 }}>PKG #{i + 1}</div>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text2)', lineHeight: 1.8, marginBottom: 8 }}>
                    <div>ID: {pkg.package_id?.slice(0, 28)}...</div>
                    {pkg.plan_id && <div>PLAN: <span style={{ color: 'var(--accent)' }}>{pkg.plan_id}</span></div>}
                    <div>STATUS: <span style={{ color: 'var(--green)' }}>{pkg.package_status || 'ready'}</span></div>
                    {pkg.created_at && <div>{new Date(pkg.created_at).toLocaleString('ko-KR')}</div>}
                  </div>
                  <Btn v="ghost" sm loading={decLoading} onClick={() => handleDecryptPackage(pkg)}
                    style={{ borderColor: 'var(--cyan)', color: 'var(--cyan)' }}>
                    🔓 Vault 복호화
                  </Btn>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* 복호화된 자산 목록 + 다운로드 */}
        <Card>
          <CardTitle>복호화된 자산 목록</CardTitle>
          {!decryptedPkg ? (
            <div style={{ padding: '32px 0', textAlign: 'center', fontSize: 12, color: 'var(--text3)', fontFamily: 'var(--mono)', lineHeight: 2 }}>
              ← 패키지를 복호화하면<br />자산 목록이 여기에 표시됩니다
            </div>
          ) : (
            <div>
              {/* vault 요약 + 다운로드 */}
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                marginBottom: 14, padding: '8px 10px',
                background: 'var(--surface2)', borderRadius: 'var(--r-sm)',
              }}>
                <div style={{ fontSize: 10, color: 'var(--text2)', fontFamily: 'var(--mono)', lineHeight: 1.8 }}>
                  VAULT_VERSION: {decryptedPkg.vault_contents?.vault_version || 1} ·
                  자산 {decryptedPkg.vault_contents?.assets?.length || 0}개 ·
                  PLAN: {decryptedPkg.plan_id?.slice(0, 18)}...
                </div>
                <Btn v="ghost" sm onClick={() => {
                  const vaultJson = JSON.stringify({
                    package_id: decryptedPkg.package_id,
                    plan_id: decryptedPkg.plan_id,
                    exported_at: new Date().toISOString(),
                    ...decryptedPkg.vault_contents,
                  }, null, 2)
                  const blob = new Blob([vaultJson], { type: 'application/json' })
                  const url  = URL.createObjectURL(blob)
                  const a    = document.createElement('a')
                  a.href = url
                  a.download = `key_vault_${decryptedPkg.plan_id?.slice(0, 8) || 'export'}.json`
                  a.click()
                  URL.revokeObjectURL(url)
                }} style={{ borderColor: 'var(--cyan)', color: 'var(--cyan)', flexShrink: 0 }}>
                  ⬇ Vault JSON
                </Btn>
              </div>

              {(decryptedPkg.vault_contents?.assets || []).length === 0 ? (
                <Empty msg="vault 안에 자산이 없습니다" />
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {(decryptedPkg.vault_contents?.assets || []).map((asset, i) => {
                    const isDownloading = downloadingId === asset.asset_id
                    const typeColor = TYPE_COLOR[asset.asset_type] || 'var(--text2)'
                    return (
                      <div key={i} style={{
                        background: 'var(--surface2)', border: '1px solid var(--border)',
                        borderRadius: 'var(--r-sm)', padding: '13px 14px',
                        borderLeft: `2px solid ${typeColor}`,
                      }}>
                        {/* 자산 헤더 */}
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontSize: 16 }}>{MIME_ICON[asset.mime_type] || '📦'}</span>
                            <span style={{ fontSize: 13, fontWeight: 700 }}>
                              {asset.asset_name || `자산 ${i + 1}`}
                            </span>
                          </div>
                          <span style={{
                            fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
                            background: `${typeColor}20`, color: typeColor, textTransform: 'uppercase',
                          }}>{asset.asset_type || '?'}</span>
                        </div>

                        {/* 자산 메타 */}
                        <div style={{ fontFamily: 'var(--mono)', fontSize: 10, color: 'var(--text3)', lineHeight: 1.8, marginBottom: 10 }}>
                          <div>ID: {asset.asset_id}</div>
                          <div>MIME: {asset.mime_type || '—'}</div>
                          <div>ALGO: <span style={{ color: 'var(--green)' }}>{asset.algorithm}</span></div>
                          <div>DEK: <span style={{ color: 'var(--amber)' }}>{asset.dek?.slice(0, 24)}...</span></div>
                          <div>NONCE: <span style={{ color: 'var(--accent)' }}>{asset.nonce?.slice(0, 24)}...</span></div>
                        </div>

                        {/* 다운로드 버튼 */}
                        <Btn
                          v="success" sm
                          loading={isDownloading}
                          disabled={!!downloadingId && !isDownloading}
                          onClick={() => handleDownloadAsset(asset)}
                          style={{ width: '100%', justifyContent: 'center' }}
                        >
                          {isDownloading ? '복호화 중...' : `⬇ ${asset.asset_name || '자산'} 다운로드`}
                        </Btn>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      <Card>
        <CardTitle>시스템 로그</CardTitle>
        <LogBox lines={lines} />
      </Card>
    </div>
  )
}
