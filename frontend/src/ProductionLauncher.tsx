import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Clapperboard, ExternalLink, Loader2, X } from 'lucide-react';
import { api } from './api';

export default function ProductionLauncher() {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [projectId, setProjectId] = useState('');
  const projects = useQuery({ queryKey: ['projects'], queryFn: api.projects });
  const jobs = useQuery({ queryKey: ['production-jobs'], queryFn: api.productionJobs, enabled: open });
  const eligible = (projects.data ?? []).filter((item) => item.quality_report?.pass === true && item.status !== 'PUBLISHED');
  const render = useMutation({
    mutationFn: () => api.renderProject(projectId),
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: ['projects'] }),
        client.invalidateQueries({ queryKey: ['production-jobs'] }),
        client.invalidateQueries({ queryKey: ['overview'] }),
      ]);
    },
  });

  return <>
    <button className="production-fab" onClick={() => setOpen(!open)}><Clapperboard size={18} />Render drafts</button>
    {open && <aside className="production-drawer">
      <header><div><span className="eyebrow">LOCAL MEDIA WORKER</span><h3>Draft production</h3></div><button className="icon-button" onClick={() => setOpen(false)}><X size={16} /></button></header>
      <p className="drawer-copy">Creates a basic local MP4 and SRT. Replace placeholder visuals and review the result before publishing.</p>
      <label>Quality-approved project<select value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Choose a project</option>{eligible.map((item) => <option key={item.id} value={item.id}>{item.title} · {item.status}</option>)}</select></label>
      <button className="primary-button" disabled={!projectId || render.isPending} onClick={() => render.mutate()}>{render.isPending ? <Loader2 className="spin" size={17} /> : <Clapperboard size={17} />}{render.isPending ? 'Rendering' : 'Render MP4 draft'}</button>
      {render.isError && <p className="error-box">{render.error instanceof Error ? render.error.message : 'Rendering failed'}</p>}
      {render.data?.output_url && <p className="notice-box"><a href={render.data.output_url} target="_blank" rel="noreferrer">Open MP4 <ExternalLink size={13} /></a></p>}
      <div className="drawer-jobs"><h4>Recent jobs</h4>{jobs.data?.slice(0, 8).map((job) => <article key={job.id}><div><strong>{job.project_title ?? job.project_id}</strong><span>{job.status}</span></div>{job.error_message && <small>{job.error_message}</small>}<div className="job-links">{job.output_url && <a href={job.output_url} target="_blank" rel="noreferrer">MP4</a>}{job.subtitle_url && <a href={job.subtitle_url} target="_blank" rel="noreferrer">SRT</a>}</div></article>)}</div>
    </aside>}
  </>;
}
