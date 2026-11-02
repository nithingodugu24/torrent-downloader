import { useDialog } from './useDialog';
import { FormEvent, useEffect, useRef, useState } from 'react';
import { FileUp, Link, X } from 'lucide-react';

interface AddTorrentModalProps {
  open: boolean;
  onClose: () => void;
  onAddMagnet: (payload: {
    magnet_uri: string;
    save_path?: string;
    category?: string;
    priority: number;
    is_sequential: boolean;
  }) => Promise<void>;
  onAddFile: (payload: {
    file: File;
    save_path?: string;
    category?: string;
    priority: number;
    is_sequential: boolean;
  }) => Promise<void>;
}

export function AddTorrentModal({
  open,
  onClose,
  onAddMagnet,
  onAddFile
}: AddTorrentModalProps) {
  const [mode, setMode] = useState<'magnet' | 'file'>('magnet');
  const [magnet, setMagnet] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [savePath, setSavePath] = useState('');
  const [category, setCategory] = useState('');
  const [priority, setPriority] = useState(4);
  const [isSequential, setSequential] = useState(false);
  const [busy, setBusy] = useState(false);

  const [error, setError] = useState('');
  const formRef = useRef<HTMLFormElement>(null);
  useDialog(
    formRef,
    open,
    () => {
      if (!busy) onClose();
    },
    'textarea, input'
  );
  useEffect(() => {
    if (open) setError('');
  }, [open]);
  if (!open) return null;

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      if (mode === 'magnet') {
        await onAddMagnet({
          magnet_uri: magnet,
          save_path: savePath || undefined,
          category: category || undefined,
          priority,
          is_sequential: isSequential
        });
      } else if (file) {
        await onAddFile({
          file,
          save_path: savePath || undefined,
          category: category || undefined,
          priority,
          is_sequential: isSequential
        });
      }
      setMagnet('');
      setFile(null);
      setSavePath('');
      setCategory('');
      setPriority(4);
      setSequential(false);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Unable to add torrent. Try again.'
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-torrent-title"
    >
      <form ref={formRef} aria-busy={busy} className="modal" onSubmit={submit}>
        <div className="modal-header">
          <div>
            <h2 id="add-torrent-title">Add torrent</h2>
            <p className="modal-description">
              Start a transfer from a magnet link or torrent file.
            </p>
          </div>
          <button
            className="icon-button"
            type="button"
            onClick={onClose}
            title="Close"
            aria-label="Close add torrent"
            disabled={busy}
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <fieldset disabled={busy} className="add-fields">
          <div className="segmented">
            <button
              type="button"
              aria-pressed={mode === 'magnet'}
              className={mode === 'magnet' ? 'active' : ''}
              onClick={() => setMode('magnet')}
            >
              <Link size={16} aria-hidden="true" />
              Magnet
            </button>
            <button
              type="button"
              aria-pressed={mode === 'file'}
              className={mode === 'file' ? 'active' : ''}
              onClick={() => setMode('file')}
            >
              <FileUp size={16} aria-hidden="true" />
              File
            </button>
          </div>
          {mode === 'magnet' ? (
            <label className="field">
              Magnet URI
              <textarea
                value={magnet}
                onChange={(event) => setMagnet(event.target.value)}
                required
                rows={4}
                placeholder="magnet:?xt=urn:btih:..."
              />
            </label>
          ) : (
            <label className="field">
              .torrent File
              <input
                type="file"
                accept=".torrent"
                required
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </label>
          )}
          <p className="field-help">
            Use a torrent you own or have permission to download.
          </p>
          <details className="add-options">
            <summary>Transfer options</summary>
            <div className="form-grid">
              <label className="field">
                Save path
                <input
                  placeholder="Default downloads folder"
                  value={savePath}
                  onChange={(event) => setSavePath(event.target.value)}
                />
              </label>
              <label className="field">
                Category
                <input
                  placeholder="Optional"
                  value={category}
                  onChange={(event) => setCategory(event.target.value)}
                />
              </label>
              <label className="field">
                Priority
                <input
                  type="number"
                  min="0"
                  max="7"
                  value={priority}
                  onChange={(event) => setPriority(Number(event.target.value))}
                />
              </label>
              <label className="check-field">
                <input
                  type="checkbox"
                  checked={isSequential}
                  onChange={(event) => setSequential(event.target.checked)}
                />
                Sequential download
              </label>
            </div>
          </details>
        </fieldset>
        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}
        <div className="modal-actions">
          <button
            type="button"
            className="ghost-button"
            disabled={busy}
            onClick={onClose}
          >
            Cancel
          </button>
          <button type="submit" className="primary-button" disabled={busy}>
            {busy ? 'Adding torrent...' : 'Add torrent'}
          </button>
        </div>
      </form>
    </div>
  );
}
