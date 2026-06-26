import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Languages, Loader2, X } from 'lucide-react';
import { api } from './api';
import type { LanguageCode } from './types';
import VariantEditor from './VariantEditor';

const supported: Array<{ code: LanguageCode; label: string }> = [
  { code: 'en', label: 'English' },
  { code: 'it', label: 'Italian' },
  { code: 'sq', label: 'Albanian' },
  { code: 'mk', label: 'Macedonian' },
];

export default function LocalizationLauncher() {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [projectId, setProjectId] = useState('');
  const [selected, setSelected] = useState<LanguageCode[]>(supported.map((item) => item.code));
  const [glossaryText, setGlossaryText] = useState('');
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.projects });
  const variants = useQuery({
    queryKey: ['localized-variants', projectId],
    queryFn: () => api.variants(projectId),
    enabled: Boolean(projectId),
  });
  const generate = useMutation({
    mutationFn: () => {
      const entries = glossaryText.split('\n').map((line) => line.split('=', 2).map((part) => part.trim())).filter((parts) => parts.length === 2 && parts[0]);
      return api.generateVariants(projectId, { languages: selected, glossary: Object.fromEntries(entries), overwrite: true });
    },
    onSuccess: () => client.invalidateQueries({ queryKey: ['localized-variants', projectId] }),
  });

  function toggle(code: LanguageCode) {
    setSelected((current) => current.includes(code) ? current.filter((item) => item !== code) : [...current, code]);
  }

  return <>
    <button className="localization-fab" onClick={() => setOpen(!open)}><Languages size={18} />Languages</button>
    {open && <aside className="localization-drawer">
      <header><div><span className="eyebrow">MULTI-LANGUAGE FACTORY</span><h3>Content variants</h3></div><button className="icon-button" onClick={() => setOpen(false)}><X size={16} /></button></header>
      <p className="drawer-copy">Create independent language versions. Each one must be reviewed and approved by a human.</p>
      <label>Project<select value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Choose a project</option>{projects.data?.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}</select></label>
      <div className="language-options">{supported.map((item) => <label key={item.code}><input type="checkbox" checked={selected.includes(item.code)} onChange={() => toggle(item.code)} />{item.label}</label>)}</div>
      <label>Glossary, one term per line<textarea rows={4} value={glossaryText} onChange={(event) => setGlossaryText(event.target.value)} placeholder={'GNSS=GNSS\nGeoElaborat=GeoElaborat'} /></label>
      <button className="primary-button" disabled={!projectId || selected.length === 0 || generate.isPending} onClick={() => generate.mutate()}>{generate.isPending ? <Loader2 className="spin" size={17} /> : <Languages size={17} />}{generate.isPending ? 'Generating variants' : 'Generate or refresh variants'}</button>
      {generate.isError && <p className="error-box">{generate.error instanceof Error ? generate.error.message : 'Localization failed'}</p>}
      <div className="variant-list">{variants.data?.map((variant) => <VariantEditor key={variant.id} variant={variant} />)}</div>
    </aside>}
  </>;
}
