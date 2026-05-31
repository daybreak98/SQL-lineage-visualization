import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import App from '../App';

// ══════════════════════════════════════════════════════════════
//  Mocks
// ══════════════════════════════════════════════════════════════

// Monaco Editor — avoid loading the full editor in jsdom
vi.mock('@monaco-editor/react', () => ({
  default: ({
    value,
    onChange,
  }: {
    value?: string;
    onChange?: (v: string) => void;
  }) => (
    <div data-testid="monaco-editor">
      <textarea
        data-testid="monaco-textarea"
        value={value ?? ''}
        onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
          onChange?.(e.target.value)
        }
        readOnly
      />
    </div>
  ),
  loader: { config: vi.fn() },
}));

// API client — control responses from test
const mockAnalyzeSql = vi.fn();
const mockFormatSql = vi.fn();
const mockGetHealth = vi.fn();
const mockListMetadataTables = vi.fn();
const mockListMetadataColumns = vi.fn();

vi.mock('../api/client', () => ({
  analyzeSql: (...args: unknown[]) => mockAnalyzeSql(...args),
  formatSql: (...args: unknown[]) => mockFormatSql(...args),
  getHealth: (...args: unknown[]) => mockGetHealth(...args),
  listMetadataTables: (...args: unknown[]) => mockListMetadataTables(...args),
  listMetadataColumns: (...args: unknown[]) => mockListMetadataColumns(...args),
  previewMetadata: vi.fn(),
  commitMetadata: vi.fn(),
}));

// ══════════════════════════════════════════════════════════════
//  Helpers
// ══════════════════════════════════════════════════════════════

const successResult = {
  analysis_id: 'test-analysis-1',
  status: 'success' as const,
  tables_extracted: ['users', 'orders'],
  columns_extracted: ['id', 'name', 'amount'],
  diagnostics_report: { diagnostics: [] },
};

const failedResult = {
  analysis_id: 'test-failed-1',
  status: 'failed' as const,
  tables_extracted: [],
  columns_extracted: [],
  diagnostics_report: {
    diagnostics: [
      {
        code: 'PARSE_ERROR',
        level: 'error' as const,
        message: 'Syntax error',
        details: {},
      },
    ],
  },
};

const partialResult = {
  analysis_id: 'test-partial-1',
  status: 'partial' as const,
  tables_extracted: ['users'],
  columns_extracted: ['id'],
  diagnostics_report: {
    diagnostics: [
      {
        code: 'WARNING',
        level: 'warning' as const,
        message: 'Incomplete metadata',
        details: {},
      },
    ],
  },
};

// ══════════════════════════════════════════════════════════════
//  Tests
// ══════════════════════════════════════════════════════════════

describe('Analyze Flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: backend is healthy with metadata present
    mockGetHealth.mockResolvedValue({
      status: 'ok',
      service: 'sql-lineage',
      version: '1.0.0',
    });
    mockListMetadataTables.mockResolvedValue({
      tables: [{ name: 'users' }, { name: 'orders' }],
      total: 2,
    });
  });

  // ── Initial render ─────────────────────────────────────────

  it('renders the app shell without crashing', () => {
    render(<App />);
    expect(screen.getByText('SQL Lineage')).toBeInTheDocument();
  });

  it('shows Analyze button on load', () => {
    render(<App />);
    const analyzeBtn = screen.getByText('Analyze');
    expect(analyzeBtn).toBeInTheDocument();
    expect(analyzeBtn.tagName).toBe('BUTTON');
  });

  // ── Loading / analyzing state ──────────────────────────────

  it('shows loading state (Cancel button) during analyze', async () => {
    // Make analyzeSql never resolve so we stay in "analyzing"
    mockAnalyzeSql.mockReturnValue(new Promise(() => {}));

    render(<App />);

    fireEvent.click(screen.getByText('Analyze'));

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    // The state pill should show 'analyzing'
    await waitFor(() => {
      const pills = screen.getAllByText(/analyzing/);
      expect(pills.length).toBeGreaterThan(0);
    });
  });

  // ── Analyze success ────────────────────────────────────────

  it('shows trusted state after analyze success', async () => {
    mockAnalyzeSql.mockResolvedValueOnce(successResult);

    render(<App />);

    fireEvent.click(screen.getByText('Analyze'));

    await waitFor(() => {
      const trustedEls = screen.getAllByText('trusted');
      expect(trustedEls.length).toBeGreaterThan(0);
    });
  });

  it('shows analyzed status after analyze success', async () => {
    mockAnalyzeSql.mockResolvedValueOnce(successResult);

    render(<App />);

    fireEvent.click(screen.getByText('Analyze'));

    await waitFor(() => {
      const els = screen.getAllByText(/analyzed/);
      // "analyzed" appears in TopBar status pill
      expect(els.length).toBeGreaterThan(0);
    });
  });

  // ── Analyze failure ────────────────────────────────────────

  it('shows error state on analyze failure (backend returns failed)', async () => {
    mockAnalyzeSql.mockResolvedValueOnce(failedResult);

    render(<App />);

    fireEvent.click(screen.getByText('Analyze'));

    await waitFor(() => {
      const failedEls = screen.getAllByText(/failed/);
      expect(failedEls.length).toBeGreaterThan(0);
    });
  });

  it('shows error state on network error', async () => {
    mockAnalyzeSql.mockRejectedValueOnce(new Error('Network failure'));

    render(<App />);

    fireEvent.click(screen.getByText('Analyze'));

    await waitFor(() => {
      const failedEls = screen.getAllByText(/failed/);
      expect(failedEls.length).toBeGreaterThan(0);
    });
  });

  // ── Dirty / stale after edit ───────────────────────────────

  it('marks state as dirty/stale when SQL is changed after analyze', async () => {
    mockAnalyzeSql.mockResolvedValueOnce(successResult);

    render(<App />);

    // 1. Run analyze — get to trusted state
    fireEvent.click(screen.getByText('Analyze'));

    await waitFor(() => {
      const trustedEls = screen.getAllByText('trusted');
      expect(trustedEls.length).toBeGreaterThan(0);
    });

    // 2. Edit the SQL via mocked Monaco textarea
    const textarea = screen.getByTestId('monaco-textarea');
    fireEvent.change(textarea, {
      target: { value: 'SELECT * FROM new_table' },
    });

    // 3. Should show stale / dirty
    await waitFor(() => {
      const staleEls = screen.getAllByText('stale');
      expect(staleEls.length).toBeGreaterThan(0);
    });

    // 4. Button should now say "Re-analyze" (pageMode === 'dirty')
    expect(screen.getByText('Re-analyze')).toBeInTheDocument();
  });

  // ── Partial analysis ───────────────────────────────────────

  it('shows trusted state for partial analysis', async () => {
    mockAnalyzeSql.mockResolvedValueOnce(partialResult);

    render(<App />);

    fireEvent.click(screen.getByText('Analyze'));

    await waitFor(() => {
      const trustedEls = screen.getAllByText('trusted');
      expect(trustedEls.length).toBeGreaterThan(0);
    });
  });

  // ── Load Example button ────────────────────────────────────

  it('keeps drawer collapsed after partial analysis until the user opens it', async () => {
    mockAnalyzeSql.mockResolvedValueOnce(partialResult);

    render(<App />);

    fireEvent.click(screen.getByText('Analyze'));

    await waitFor(() => {
      const partialEls = screen.getAllByText(/partial/);
      expect(partialEls.length).toBeGreaterThan(0);
    });

    expect(document.querySelector('.drawer.open')).toBeNull();
  });

  it('resets state when Load Example is clicked after analyze', async () => {
    mockAnalyzeSql.mockResolvedValueOnce(successResult);

    render(<App />);

    // Run analyze first
    fireEvent.click(screen.getByText('Analyze'));

    await waitFor(() => {
      const trustedEls = screen.getAllByText('trusted');
      expect(trustedEls.length).toBeGreaterThan(0);
    });

    // Click Load Example
    fireEvent.click(screen.getByText('Load Example'));

    await waitFor(() => {
      const untrustedEls = screen.getAllByText('untrusted');
      expect(untrustedEls.length).toBeGreaterThan(0);
    });
  });
});
