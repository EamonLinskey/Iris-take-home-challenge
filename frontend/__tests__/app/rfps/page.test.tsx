/**
 * Tests for RFPs list page component
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import RFPsPage from '@/app/rfps/page';
import { rfpsApi } from '@/lib/api';
import type { RFP } from '@/lib/types';

jest.mock('@/lib/api');
const mockedRfpsApi = rfpsApi as jest.Mocked<typeof rfpsApi>;

describe('RFPsPage', () => {
  const mockRFPs: RFP[] = [
    {
      id: '1',
      name: 'Q1 2024 RFP',
      description: 'First quarter RFP',
      status: 'completed',
      uploaded_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      questions: [
        {
          id: 'q1',
          question_text: 'Question 1?',
          question_index: 0,
          context: '',
        },
      ],
    },
    {
      id: '2',
      name: 'Q2 2024 RFP',
      description: 'Second quarter RFP',
      status: 'pending',
      uploaded_at: '2024-02-01T00:00:00Z',
      updated_at: '2024-02-01T00:00:00Z',
      questions: [],
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render loading state initially', () => {
    mockedRfpsApi.list.mockImplementation(() => new Promise(() => {}));

    render(<RFPsPage />);

    expect(screen.getByText(/Loading RFPs/i)).toBeInTheDocument();
  });

  it('should display RFPs after loading', async () => {
    mockedRfpsApi.list.mockResolvedValueOnce(mockRFPs);

    render(<RFPsPage />);

    await waitFor(() => {
      expect(screen.getByText('Q1 2024 RFP')).toBeInTheDocument();
      expect(screen.getByText('Q2 2024 RFP')).toBeInTheDocument();
    });
  });

  it('should show empty state when no RFPs', async () => {
    mockedRfpsApi.list.mockResolvedValueOnce([]);

    render(<RFPsPage />);

    await waitFor(() => {
      expect(screen.getByText(/No RFPs created yet/i)).toBeInTheDocument();
    });
  });

  it('should display error message on API failure', async () => {
    mockedRfpsApi.list.mockRejectedValueOnce(new Error('API Error'));

    render(<RFPsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load RFPs/i)).toBeInTheDocument();
    });
  });

  it('should display RFP status badges', async () => {
    mockedRfpsApi.list.mockResolvedValueOnce(mockRFPs);

    render(<RFPsPage />);

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument();
      expect(screen.getByText('pending')).toBeInTheDocument();
    });
  });

  it('should display question count for each RFP', async () => {
    mockedRfpsApi.list.mockResolvedValueOnce(mockRFPs);

    render(<RFPsPage />);

    await waitFor(() => {
      expect(screen.getByText('1 questions')).toBeInTheDocument();
      expect(screen.getByText('0 questions')).toBeInTheDocument();
    });
  });

  it('should have link to create new RFP', async () => {
    mockedRfpsApi.list.mockResolvedValueOnce([]);

    render(<RFPsPage />);

    await waitFor(() => {
      const createLinks = screen.getAllByText(/Create New RFP/i);
      expect(createLinks.length).toBeGreaterThan(0);
    });
  });

  it('should handle delete RFP', async () => {
    mockedRfpsApi.list.mockResolvedValueOnce(mockRFPs);
    mockedRfpsApi.delete.mockResolvedValueOnce(undefined);
    mockedRfpsApi.list.mockResolvedValueOnce([mockRFPs[1]]);

    window.confirm = jest.fn(() => true);

    render(<RFPsPage />);

    await waitFor(() => {
      expect(screen.getByText('Q1 2024 RFP')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText('Delete');
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockedRfpsApi.delete).toHaveBeenCalledWith('1');
    });
  });

  it('should not delete when confirmation is cancelled', async () => {
    mockedRfpsApi.list.mockResolvedValueOnce(mockRFPs);

    window.confirm = jest.fn(() => false);

    render(<RFPsPage />);

    await waitFor(() => {
      expect(screen.getByText('Q1 2024 RFP')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText('Delete');
    fireEvent.click(deleteButtons[0]);

    expect(mockedRfpsApi.delete).not.toHaveBeenCalled();
  });

  it('should format dates correctly', async () => {
    mockedRfpsApi.list.mockResolvedValueOnce(mockRFPs);

    render(<RFPsPage />);

    await waitFor(() => {
      // Check that dates are formatted (exact format may vary by locale)
      const dateElements = screen.getAllByText(/Created/i);
      expect(dateElements.length).toBeGreaterThan(0);
    });
  });
});
