import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, Save } from 'lucide-react';
import { api } from './api';
import type { LocalizedVariant } from './types';

export default function VariantEditor({ variant }: { variant: LocalizedVariant }) {
  const client = useQueryClient();
  const [title, setTitle] = useState(variant.title);
  const [hook, setHook] = useState(variant.hook);
  const [narration, setNarration] = useState(variant.narration);
  const [description, setDescription] = useState(variant.description);
  const save = useMutation({
    mutationFn: (reviewStatus?: LocalizedVariant['review_status']) => api.updateVariant(variant.id, {
      title,
      hook,
      narration,
      description,
      review_status: reviewStatus ?? variant.review_status,
    }),
    onSuccess: () => client.invalidateQueries({ queryKey: ['localized-variants', variant.project_id] }),
  });

  return <article className="variant-card">
    <header>
      <div><strong>{variant.language_name}</strong><small>{variant.language_code.toUpperCase()} · {variant.review_status.replace('_', ' ')}</small></div>
      {variant.review_status === 'APPROVED' && <Check size={18} />}
    </header>
    <label>Title<input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
    <label>Hook<textarea rows={3} value={hook} onChange={(event) => setHook(event.target.value)} /></label>
    <label>Narration<textarea rows={10} value={narration} onChange={(event) => setNarration(event.target.value)} /></label>
    <label>Description<textarea rows={4} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
    {variant.translation_notes && <p className="notice-box">{variant.translation_notes}</p>}
    <div className="button-row">
      <button className="secondary-button" disabled={save.isPending} onClick={() => save.mutate(undefined)}><Save size={15} />Save edits</button>
      <button className="primary-button" disabled={save.isPending} onClick={() => save.mutate('APPROVED')}><Check size={15} />Approve language</button>
    </div>
    {save.isError && <p className="error-box">{save.error instanceof Error ? save.error.message : 'Could not save variant'}</p>}
  </article>;
}
