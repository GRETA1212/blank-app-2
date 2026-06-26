import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Clapperboard, Download, Loader2, Play, X } from 'lucide-react';
import { api } from './api';
import type { LanguageCode } from './types';

const message = (value: unknown) => value instanceof Error ? value.message : 'Audio operation failed';

export default function AudioStudioLauncher() {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [projectId, setProjectId] = useState('');
  const [variantId, setVariantId] = useState('');
  const [voiceId, setVoiceId] = useState('');
  const [speed, setSpeed] = useState(1);
  const [previewUrl, setPreviewUrl] = useState('');
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.projects });
  const variants = useQuery({ queryKey: ['localized-variants', projectId], queryFn: () => api.variants(projectId), enabled: Boolean(projectId) });
  const project = projects.data?.find((item) => item.id === projectId);
  const variant = variants.data?.find((item) => item.id === variantId);
  const language: LanguageCode = variant?.language_code ?? 'en';
  const voices = useQuery({ queryKey: ['enhanced-voices', language], queryFn: () => api.enhancedVoices(language), enabled: open });
  const jobs = useQuery({ queryKey: ['production-jobs'], queryFn: api.productionJobs, enabled: open });
  const voice = voices.data?.voices.find((item) => item.id === voiceId);
  const text = variant?.narration ?? project?.narration ?? '';

  useEffect(() => { setVariantId(''); setPreviewUrl(''); }, [projectId]);
  useEffect(() => { const preferred = variant?.voice_id ?? voices.data?.defaults?.[language]; if (preferred) setVoiceId(preferred); }, [language, variant?.voice_id, voices.data]);

  const install = useMutation({ mutationFn: () => api.installVoice(voiceId), onSuccess: () => client.invalidateQueries({ queryKey: ['enhanced-voices', language] }) });
  const preview = useMutation({ mutationFn: () => api.previewEnhancedVoice({ text: text.slice(0, 500), language_code: language, voice_id: voiceId || null, speed }), onSuccess: (data) => setPreviewUrl(data.audio_url) });
  const render = useMutation({
    mutationFn: () => api.renderEnhanced(projectId, { aspect_ratio: '16:9', content_variant_id: variantId || null, language_code: language, voice_id: voiceId || null, voice_speed: speed, burn_subtitles: true, verify_subtitles: true }),
    onSuccess: () => Promise.all([client.invalidateQueries({ queryKey: ['projects'] }), client.invalidateQueries({ queryKey: ['production-jobs'] }), client.invalidateQueries({ queryKey: ['overview'] })]),
  });
  const blocked = !projectId || Boolean(variantId && variant?.review_status !== 'APPROVED') || Boolean(voice && voice.engine === 'piper' && !voice.installed);
  const error = install.error ?? preview.error ?? render.error;
  const verification = render.data?.renderer?.subtitle_verification ?? render.data?.subtitle_verification;
  const eligible = (projects.data ?? []).filter((item) => item.quality_report?.pass === true && item.status !== 'PUBLISHED');

  return <>
    <button className="production-fab" onClick={() => setOpen(!open)}><Clapperboard size={18} />Audio studio</button>
    {open && <aside className="production-drawer">
      <header><div><span className="eyebrow">LOCAL AUDIO STUDIO</span><h3>Voice and subtitles</h3></div><button className="icon-button" onClick={() => setOpen(false)}><X size={16} /></button></header>
      <label>Project<select value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Choose a project</option>{eligible.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
      <label>Language version<select value={variantId} onChange={(event) => setVariantId(event.target.value)}><option value="">English master</option>{variants.data?.map((item) => <option key={item.id} value={item.id}>{item.language_name} · {item.review_status}</option>)}</select></label>
      <label>Voice<select value={voiceId} onChange={(event) => setVoiceId(event.target.value)}>{voices.data?.voices.map((item) => <option key={item.id} value={item.id}>{item.display_name}{item.installed ? '' : ' · install'}</option>)}</select></label>
      {voice && !voice.installed && voice.engine === 'piper' && <button className="secondary-button" onClick={() => install.mutate()} disabled={install.isPending}><Download size={15} />Install voice</button>}
      <label>Speed {speed.toFixed(2)}×<input type="range" min="0.65" max="1.5" step="0.05" value={speed} onChange={(event) => setSpeed(Number(event.target.value))} /></label>
      <button className="secondary-button" disabled={blocked || !text || preview.isPending} onClick={() => preview.mutate()}>{preview.isPending ? <Loader2 className="spin" size={15} /> : <Play size={15} />}Preview</button>
      {previewUrl && <audio controls src={previewUrl} className="voice-preview" />}
      <button className="primary-button" disabled={blocked || render.isPending} onClick={() => render.mutate()}>{render.isPending ? <Loader2 className="spin" size={17} /> : <Clapperboard size={17} />}Render and verify</button>
      {variantId && variant?.review_status !== 'APPROVED' && <p className="error-box">Approve this language variant first.</p>}
      {error && <p className="error-box">{message(error)}</p>}
      {render.data?.output_url && <div className="verification-card"><a href={render.data.output_url} target="_blank" rel="noreferrer">MP4</a> · <a href={render.data.subtitle_url ?? '#'} target="_blank" rel="noreferrer">SRT</a> · <a href={render.data.transcript_url ?? '#'} target="_blank" rel="noreferrer">Transcript</a><strong>{verification?.similarity == null ? 'Verification unavailable' : `Transcript match ${(verification.similarity * 100).toFixed(1)}%`}</strong>{verification?.warning && <small>{verification.warning}</small>}</div>}
      <div className="drawer-jobs"><h4>Recent jobs</h4>{jobs.data?.slice(0, 6).map((job) => <article key={job.id}><div><strong>{job.project_title ?? job.project_id}</strong><span>{job.language_code?.toUpperCase() ?? 'EN'} · {job.status}</span></div><small>{job.voice_engine ?? job.voice_id ?? 'Voice pending'}</small></article>)}</div>
    </aside>}
  </>;
}
