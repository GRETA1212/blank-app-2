import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Clapperboard, Download, ExternalLink, Loader2, Play, X } from 'lucide-react';
import { api } from './api';
import type { LanguageCode, VoiceOption } from './types';

export default function ProductionLauncher() {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [projectId, setProjectId] = useState('');
  const [variantId, setVariantId] = useState('');
  const [voiceId, setVoiceId] = useState('');
  const [speed, setSpeed] = useState(1);
  const [previewUrl, setPreviewUrl] = useState('');
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.projects });
  const variants = useQuery({ queryKey: ['localized-variants', projectId], queryFn: () => api.variants(projectId), enabled: Boolean(projectId) });
  const selectedProject = projects.data?.find((item) => item.id === projectId);
  const selectedVariant = variants.data?.find((item) => item.id === variantId);
  const languageCode: LanguageCode = selectedVariant?.language_code ?? 'en';
  const voices = useQuery({ queryKey: ['enhanced-voices', languageCode], queryFn: () => api.enhancedVoices(languageCode), enabled: open });
  const jobs = useQuery({ queryKey: ['production-jobs'], queryFn: api.productionJobs, enabled: open });
  const eligible = (projects.data ?? []).filter((item) => item.quality_report?.pass === true && item.status !== 'PUBLISHED');
  const selectedVoice = voices.data?.voices.find((item) => item.id === voiceId);
  const contentText = selectedVariant?.narration ?? selectedProject?.narration ?? '';
  const verification = render.data?.renderer?.subtitle_verification ?? render.data?.subtitle_verification;

  useEffect(() => {
    setVariantId('');
    setPreviewUrl('');
  }, [projectId]);

  useEffect(() => {
    const preferred = selectedVariant?.voice_id ?? voices.data?.defaults?.[languageCode];
    if (preferred) setVoiceId(preferred);
  }, [languageCode, selectedVariant?.voice_id, voices.data]);

  const install = useMutation({
    mutationFn: (voice: VoiceOption) => api.installVoice(voice.id),
    onSuccess: () => client.invalidateQueries({ queryKey: ['enhanced-voices', languageCode] }),
  });
  const preview = useMutation({
    mutationFn: () => api.previewEnhancedVoice({ text: contentText.slice(0, 500), language_code: languageCode, voice_id: voiceId || null, speed }),
    onSuccess: (data) => setPreviewUrl(data.audio_url),
  });
  const render = useMutation({
    mutationFn: () => api.renderEnhanced(projectId, {
      aspect_ratio: '16:9',
      content_variant_id: variantId || null,
      language_code: languageCode,
      voice_id: voiceId || null,
      voice_speed: speed,
      burn_subtitles: true,
      verify_subtitles: true,
    }),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ['projects'] }),
        client.invalidateQueries({ queryKey: ['production-jobs'] }),
        client.invalidateQueries({ queryKey: ['overview'] }),
      ]);
    },
  });

  const renderBlocked = useMemo(() => {
    if (!projectId) return true;
    if (variantId && selectedVariant?.review_status !== 'APPROVED') return true;
    return Boolean(selectedVoice && !selectedVoice.installed && selectedVoice.engine === 'piper');
  }, [projectId, variantId, selectedVariant?.review_status, selectedVoice]);

  return <>
    <button className="production-fab" onClick={() => setOpen(!open)}><Clapperboard size={18} />Render drafts</button>
    {open && <aside className="production-drawer">
      <header><div><span className="eyebrow">LOCAL AUDIO STUDIO</span><h3>Voice and verified subtitles</h3></div><button className="icon-button" onClick={() => setOpen(false)}><X size={16} /></button></header>
      <p className="drawer-copy">Choose the master or an approved language variant. Whisper transcribes the actual generated audio and compares it with the intended script.</p>
      <label>Quality-approved project<select value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Choose a project</option>{eligible.map((item) => <option key={item.id} value={item.id}>{item.title} · {item.status}</option>)}</select></label>
      <label>Language version<select value={variantId} onChange={(event) => { setVariantId(event.target.value); setPreviewUrl(''); }}><option value="">English master</option>{variants.data?.map((item) => <option key={item.id} value={item.id}>{item.language_name} · {item.review_status.replace('_', ' ')}</option>)}</select></label>
      <label>Voice<select value={voiceId} onChange={(event) => { setVoiceId(event.target.value); setPreviewUrl(''); }}><option value="">Automatic fallback</option>{voices.data?.voices.map((voice) => <option key={voice.id} value={voice.id}>{voice.display_name}{voice.installed ? '' : ' · download required'}</option>)}</select></label>
      {selectedVoice?.license_review_required && <p className="notice-box">Review this voice model's model card and licence before commercial distribution.</p>}
      {selectedVoice && !selectedVoice.installed && selectedVoice.engine === 'piper' && <button className="secondary-button" disabled={install.isPending} onClick={() => install.mutate(selectedVoice)}>{install.isPending ? <Loader2 className="spin" size={15} /> : <Download size={15} />}Install neural voice</button>}
      <label>Speaking speed<input type="range" min="0.65" max="1.5" step="0.05" value={speed} onChange={(event) => setSpeed(Number(event.target.value))} /><span>{speed.toFixed(2)}×</span></label>
      <button className="secondary-button" disabled={!contentText || preview.isPending || renderBlocked} onClick={() => preview.mutate()}>{preview.isPending ? <Loader2 className="spin" size={15} /> : <Play size={15} />}Preview voice</button>
      {previewUrl && <audio controls src={previewUrl} className="voice-preview" />}
      <button className="primary-button" disabled={renderBlocked || render.isPending} onClick={() => render.mutate()}>{render.isPending ? <Loader2 className="spin" size={17} /> : <Clapperboard size={17} />}{render.isPending ? 'Rendering and transcribing' : 'Render verified MP4 draft'}</button>
      {variantId && selectedVariant?.review_status !== 'APPROVED' && <p className="error-box">Approve this language version in the Languages drawer before rendering.</p>}
      {(preview.isError || render.isError || install.isError) && <p className="error-box">{String((preview.error ?? render.error ?? install.error) instanceof Error ? (preview.error ?? render.error ?? install.error)?.message : 'Audio operation failed')}</p>}
      {render.data?.output_url && <div className="verification-card"><a href={render.data.output_url} target="_blank" rel="noreferrer">Open MP4 <ExternalLink size={13} /></a>{render.data.subtitle_url && <a href={render.data.subtitle_url} target="_blank" rel="noreferrer">Open SRT</a>}{render.data.transcript_url && <a href={render.data.transcript_url} target="_blank" rel="noreferrer">Open transcript</a>}<strong>{verification?.similarity == null ? 'Verification unavailable' : `Transcript match ${(verification.similarity * 100).toFixed(1)}%`}</strong>{verification?.warning && <small>{verification.warning}</small>}</div>}
      <div className="drawer-jobs"><h4>Recent jobs</h4>{jobs.data?.slice(0, 8).map((job) => <article key={job.id}><div><strong>{job.project_title ?? job.project_id}</strong><span>{job.language_code?.toUpperCase() ?? 'EN'} · {job.status}</span></div><small>{job.voice_engine ?? job.voice_id ?? 'Voice pending'}</small><div className="job-links">{job.output_url && <a href={job.output_url} target="_blank" rel="noreferrer">MP4</a>}{job.subtitle_url && <a href={job.subtitle_url} target="_blank" rel="noreferrer">SRT</a>}{job.transcript_url && <a href={job.transcript_url} target="_blank" rel="noreferrer">Transcript</a>}</div></article>)}</div>
    </aside>}
  </>;
}
