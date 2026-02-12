/**
 * Tests for Create RFP page component
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import NewRFPPage from '@/app/rfps/new/page';
import { rfpsApi } from '@/lib/api';
import type { RFP } from '@/lib/types';

jest.mock('@/lib/api');
const mockedRfpsApi = rfpsApi as jest.Mocked<typeof rfpsApi>;

// Mock useRouter
const mockPush = jest.fn();
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
}));

describe('NewRFPPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render the form with initial state', () => {
    render(<NewRFPPage />);

    expect(screen.getByLabelText(/RFP Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Description/i)).toBeInTheDocument();
    expect(screen.getByText(/Question 1/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Create RFP/i })).toBeInTheDocument();
  });

  it('should allow adding questions', async () => {
    const user = userEvent.setup();

    render(<NewRFPPage />);

    const addButton = screen.getByText(/\+ Add Question/i);
    await user.click(addButton);

    expect(screen.getByText(/Question 2/i)).toBeInTheDocument();
  });

  it('should allow removing questions', async () => {
    const user = userEvent.setup();

    render(<NewRFPPage />);

    // Add a second question first
    const addButton = screen.getByText(/\+ Add Question/i);
    await user.click(addButton);

    expect(screen.getByText(/Question 2/i)).toBeInTheDocument();

    // Remove the first question
    const removeButtons = screen.getAllByText('Remove');
    await user.click(removeButtons[0]);

    // Should only have Question 1 left (which was originally Question 2)
    const questionHeaders = screen.getAllByText(/Question \d+/);
    expect(questionHeaders).toHaveLength(1);
  });

  it('should not show remove button when only one question exists', () => {
    render(<NewRFPPage />);

    const removeButtons = screen.queryAllByText('Remove');
    expect(removeButtons).toHaveLength(0);
  });

  it('should handle form submission with valid data', async () => {
    const user = userEvent.setup();

    const mockCreatedRFP: RFP = {
      id: '1',
      name: 'Test RFP',
      description: 'Test description',
      status: 'pending',
      uploaded_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      questions: [],
    };

    mockedRfpsApi.create.mockResolvedValueOnce(mockCreatedRFP);

    render(<NewRFPPage />);

    // Fill in form
    const nameInput = screen.getByLabelText(/RFP Name/i);
    const descriptionInput = screen.getByLabelText(/Description/i);
    const questionTextarea = screen.getByPlaceholderText(/e\.g\., What is your company's experience/i);

    await user.type(nameInput, 'Test RFP');
    await user.type(descriptionInput, 'Test description');
    await user.type(questionTextarea, 'What is your product?');

    // Submit form
    const submitButton = screen.getByRole('button', { name: /Create RFP/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockedRfpsApi.create).toHaveBeenCalledWith({
        name: 'Test RFP',
        description: 'Test description',
        questions: [
          {
            question_text: 'What is your product?',
            context: undefined,
          },
        ],
      });
    });

    // Should redirect to RFP detail page
    expect(mockPush).toHaveBeenCalledWith('/rfps/1');
  });

  it('should show error when name is missing', async () => {
    const user = userEvent.setup();

    render(<NewRFPPage />);

    const submitButton = screen.getByRole('button', { name: /Create RFP/i });
    await user.click(submitButton);

    expect(screen.getByText(/Please enter an RFP name/i)).toBeInTheDocument();
    expect(mockedRfpsApi.create).not.toHaveBeenCalled();
  });

  it('should show error when no questions are provided', async () => {
    const user = userEvent.setup();

    render(<NewRFPPage />);

    const nameInput = screen.getByLabelText(/RFP Name/i);
    await user.type(nameInput, 'Test RFP');

    const submitButton = screen.getByRole('button', { name: /Create RFP/i });
    await user.click(submitButton);

    expect(screen.getByText(/Please add at least one question/i)).toBeInTheDocument();
    expect(mockedRfpsApi.create).not.toHaveBeenCalled();
  });

  it('should handle API errors', async () => {
    const user = userEvent.setup();

    mockedRfpsApi.create.mockRejectedValueOnce(new Error('API Error'));

    render(<NewRFPPage />);

    // Fill in form
    const nameInput = screen.getByLabelText(/RFP Name/i);
    const questionTextarea = screen.getByPlaceholderText(/e\.g\., What is your company's experience/i);

    await user.type(nameInput, 'Test RFP');
    await user.type(questionTextarea, 'What is your product?');

    // Submit form
    const submitButton = screen.getByRole('button', { name: /Create RFP/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Failed to create RFP/i)).toBeInTheDocument();
    });
  });

  it('should disable submit button while submitting', async () => {
    const user = userEvent.setup();

    mockedRfpsApi.create.mockImplementation(() => new Promise(() => {}));

    render(<NewRFPPage />);

    const nameInput = screen.getByLabelText(/RFP Name/i);
    const questionTextarea = screen.getByPlaceholderText(/e\.g\., What is your company's experience/i);

    await user.type(nameInput, 'Test RFP');
    await user.type(questionTextarea, 'Question?');

    const submitButton = screen.getByRole('button', { name: /Create RFP/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Creating.../i })).toBeDisabled();
    });
  });

  it('should preserve context field for questions', async () => {
    const user = userEvent.setup();

    const mockCreatedRFP: RFP = {
      id: '1',
      name: 'Test RFP',
      status: 'pending',
      uploaded_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
      questions: [],
    };

    mockedRfpsApi.create.mockResolvedValueOnce(mockCreatedRFP);

    render(<NewRFPPage />);

    const nameInput = screen.getByLabelText(/RFP Name/i);
    const questionTextarea = screen.getByPlaceholderText(/e\.g\., What is your company's experience/i);
    const contextInput = screen.getByPlaceholderText(/Any additional context/i);

    await user.type(nameInput, 'Test RFP');
    await user.type(questionTextarea, 'Question?');
    await user.type(contextInput, 'Additional context');

    const submitButton = screen.getByRole('button', { name: /Create RFP/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(mockedRfpsApi.create).toHaveBeenCalledWith({
        name: 'Test RFP',
        description: undefined,
        questions: [
          {
            question_text: 'Question?',
            context: 'Additional context',
          },
        ],
      });
    });
  });
});
