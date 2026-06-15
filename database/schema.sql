CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    name TEXT,
    occupation TEXT,
    preferred_language TEXT DEFAULT 'English',
    timezone TEXT DEFAULT 'UTC',
    communication_style TEXT DEFAULT 'Concise',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    importance_score INT CHECK (importance_score BETWEEN 1 AND 10),
    embedding vector(1024),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX on memories USING hnsw (embedding vector_cosine_ops);

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INT NOT NULL,
    embedding vector(1024)
);
CREATE INDEX on document_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    due_date TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT CHECK (status IN ('todo', 'done')) DEFAULT 'todo',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'New Chat',
    summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('user', 'assistant', 'system', 'tool')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE OR REPLACE FUNCTION match_memories(query_embedding vector(1024), target_user_id UUID, match_threshold float, match_count int)
RETURNS TABLE (id UUID, content TEXT, importance_score INT, similarity FLOAT) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY SELECT m.id, m.content, m.importance_score, 1 - (m.embedding <=> query_embedding) AS similarity
    FROM memories m WHERE m.user_id = target_user_id AND 1 - (m.embedding <=> query_embedding) > match_threshold
    ORDER BY m.embedding <=> query_embedding LIMIT match_count;
END;
$$;

CREATE OR REPLACE FUNCTION match_document_chunks(query_embedding vector(1024), target_user_id UUID, match_threshold float, match_count int)
RETURNS TABLE (id UUID, content TEXT, document_id UUID, filename TEXT, similarity FLOAT) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY SELECT dc.id, dc.content, dc.document_id, d.filename, 1 - (dc.embedding <=> query_embedding) AS similarity
    FROM document_chunks dc JOIN documents d ON d.id = dc.document_id
    WHERE d.user_id = target_user_id AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding LIMIT match_count;
END;
$$;
