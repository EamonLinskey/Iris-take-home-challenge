/**
 * Tests for Documents page component
 */
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import DocumentsPage from '@/app/documents/page';
import { documentsApi } from '@/lib/api';
import type { Document } from '@/lib/types';

// Mock the API
jest.mock('@/lib/api');
const mockedDocumentsApi = documentsApi as jest.Mocked<typeof documentsApi>;

describe('DocumentsPage', () => {
  const mockDocuments: Document[] = [
    {
      id: '1',
      filename: 'test1.pdf',
      file_type: 'pdf',
      file_size: 1024,
      status: 'completed',
      uploaded_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    {
      id: '2',
      filename: 'test2.docx',
      file_type: 'docx',
      file_size: 2048,
      status: 'processing',
      uploaded_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z',
    },
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render loading state initially', () => {
    mockedDocumentsApi.list.mockImplementation(() => new Promise(() => {}));

    render(<DocumentsPage />);

    expect(screen.getByText(/Loading documents/i)).toBeInTheDocument();
  });

  it('should display documents after loading', async () => {
    mockedDocumentsApi.list.mockResolvedValueOnce(mockDocuments);

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument();
      expect(screen.getByText('test2.docx')).toBeInTheDocument();
    });
  });

  it('should show empty state when no documents', async () => {
    mockedDocumentsApi.list.mockResolvedValueOnce([]);

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText(/No documents uploaded yet/i)).toBeInTheDocument();
    });
  });

  it('should display error message on API failure', async () => {
    mockedDocumentsApi.list.mockRejectedValueOnce(new Error('API Error'));

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load documents/i)).toBeInTheDocument();
    });
  });

  it('should display document status badges', async () => {
    mockedDocumentsApi.list.mockResolvedValueOnce(mockDocuments);

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument();
      expect(screen.getByText('processing')).toBeInTheDocument();
    });
  });

  it('should format file sizes correctly', async () => {
    mockedDocumentsApi.list.mockResolvedValueOnce(mockDocuments);

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText(/1\.0 KB/)).toBeInTheDocument();
      expect(screen.getByText(/2\.0 KB/)).toBeInTheDocument();
    });
  });

  it('should handle file upload', async () => {
    mockedDocumentsApi.list.mockResolvedValueOnce([]);

    const mockFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const mockUploadedDocument: Document = {
      id: '3',
      filename: 'test.pdf',
      file_type: 'pdf',
      file_size: 1024,
      status: 'processing',
      uploaded_at: '2024-01-03T00:00:00Z',
      updated_at: '2024-01-03T00:00:00Z',
    };

    mockedDocumentsApi.upload.mockResolvedValueOnce(mockUploadedDocument);
    mockedDocumentsApi.list.mockResolvedValueOnce([mockUploadedDocument]);

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText(/No documents uploaded yet/i)).toBeInTheDocument();
    });

    const fileInput = screen.getByLabelText(/Choose File/i, { selector: 'input[type="file"]' });
    fireEvent.change(fileInput, { target: { files: [mockFile] } });

    await waitFor(() => {
      expect(mockedDocumentsApi.upload).toHaveBeenCalledWith(mockFile);
    });
  });

  it('should handle delete document', async () => {
    mockedDocumentsApi.list.mockResolvedValueOnce(mockDocuments);
    mockedDocumentsApi.delete.mockResolvedValueOnce(undefined);
    mockedDocumentsApi.list.mockResolvedValueOnce([mockDocuments[1]]);

    // Mock window.confirm
    window.confirm = jest.fn(() => true);

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText('Delete');
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(mockedDocumentsApi.delete).toHaveBeenCalledWith('1');
    });
  });

  it('should not delete when confirmation is cancelled', async () => {
    mockedDocumentsApi.list.mockResolvedValueOnce(mockDocuments);

    window.confirm = jest.fn(() => false);

    render(<DocumentsPage />);

    await waitFor(() => {
      expect(screen.getByText('test1.pdf')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText('Delete');
    fireEvent.click(deleteButtons[0]);

    expect(mockedDocumentsApi.delete).not.toHaveBeenCalled();
  });
});
