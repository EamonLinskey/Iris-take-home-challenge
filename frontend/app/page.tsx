import Link from "next/link";

export default function Home() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          AI-Powered RFP Answer Generator
        </h1>
        <p className="text-xl text-gray-600 max-w-3xl mx-auto">
          Upload your company documents, create RFP questions, and generate professional answers
          using advanced RAG (Retrieval Augmented Generation) technology powered by Claude.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8 mt-16">
        <div className="bg-white p-8 rounded-lg shadow-md border border-gray-200">
          <div className="text-3xl mb-4">📄</div>
          <h2 className="text-2xl font-semibold mb-3">1. Upload Documents</h2>
          <p className="text-gray-600 mb-6">
            Upload your company knowledge base documents (PDF, DOCX, or TXT). The system will
            automatically process and index them for intelligent retrieval.
          </p>
          <Link
            href="/documents"
            className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition"
          >
            Manage Documents
          </Link>
        </div>

        <div className="bg-white p-8 rounded-lg shadow-md border border-gray-200">
          <div className="text-3xl mb-4">✍️</div>
          <h2 className="text-2xl font-semibold mb-3">2. Create RFPs</h2>
          <p className="text-gray-600 mb-6">
            Create RFPs with multiple questions. The AI will automatically search your knowledge
            base and generate professional, accurate answers with source attribution.
          </p>
          <Link
            href="/rfps"
            className="inline-block bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition"
          >
            View RFPs
          </Link>
        </div>
      </div>

      <div className="mt-16 bg-blue-50 border border-blue-200 rounded-lg p-8">
        <h3 className="text-xl font-semibold mb-3 text-blue-900">How It Works</h3>
        <ol className="space-y-3 text-gray-700">
          <li className="flex items-start">
            <span className="font-semibold mr-2">1.</span>
            <span>Documents are chunked and embedded using sentence-transformers</span>
          </li>
          <li className="flex items-start">
            <span className="font-semibold mr-2">2.</span>
            <span>Vectors are stored in ChromaDB for fast semantic search</span>
          </li>
          <li className="flex items-start">
            <span className="font-semibold mr-2">3.</span>
            <span>Questions are matched with relevant document chunks using cosine similarity</span>
          </li>
          <li className="flex items-start">
            <span className="font-semibold mr-2">4.</span>
            <span>Claude generates professional answers based on retrieved context</span>
          </li>
        </ol>
      </div>
    </div>
  );
}
