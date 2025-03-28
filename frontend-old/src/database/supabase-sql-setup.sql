-- Supabase SQL initialization script
-- This script sets up all the necessary tables and permissions for the Morning Coffee app

-- Enable the UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Profiles table
CREATE TABLE IF NOT EXISTS profiles (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  first_name TEXT,
  last_name TEXT,
  phone_number TEXT UNIQUE,
  timezone TEXT DEFAULT 'UTC',
  preferred_voice TEXT DEFAULT 'default',
  notification_preferences JSONB DEFAULT '{"sms": true, "email": true}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  PRIMARY KEY (id)
);

-- Affirmations table
CREATE TABLE IF NOT EXISTS affirmations (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  text TEXT NOT NULL,
  category TEXT NOT NULL,
  created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  is_custom BOOLEAN DEFAULT TRUE,
  is_public BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Scheduled calls table
CREATE TABLE IF NOT EXISTS scheduled_calls (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  schedule_type TEXT NOT NULL CHECK (schedule_type IN ('daily', 'weekdays', 'weekends', 'custom')),
  schedule_config JSONB DEFAULT '{}'::jsonb,
  time TIME NOT NULL,
  timezone TEXT DEFAULT 'UTC',
  enabled BOOLEAN DEFAULT TRUE,
  affirmation_category TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Call history table
CREATE TABLE IF NOT EXISTS call_history (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  call_control_id TEXT UNIQUE,
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  ended_at TIMESTAMP WITH TIME ZONE,
  duration INTEGER, -- in seconds
  status TEXT CHECK (status IN ('init', 'greeting', 'recording_affirmation', 'chat_intro', 'recording_chat', 'ai_response', 'ended')),
  affirmation TEXT,
  transcription_count INTEGER DEFAULT 0,
  recording_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Transcriptions table
CREATE TABLE IF NOT EXISTS transcriptions (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  call_id UUID REFERENCES call_history(id) ON DELETE CASCADE NOT NULL,
  transcription_job_id TEXT UNIQUE,
  text TEXT,
  status TEXT CHECK (status IN ('pending', 'in_progress', 'completed', 'error')),
  error TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITH TIME ZONE
);

-- Organizations table (for team features)
CREATE TABLE IF NOT EXISTS organizations (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  name TEXT NOT NULL,
  owner_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Organization members table
CREATE TABLE IF NOT EXISTS organization_members (
  organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT CHECK (role IN ('owner', 'admin', 'member')),
  joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  PRIMARY KEY (organization_id, user_id)
);

-- Organization invitations table
CREATE TABLE IF NOT EXISTS organization_invitations (
  id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
  organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  role TEXT CHECK (role IN ('admin', 'member')),
  invited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  accepted_at TIMESTAMP WITH TIME ZONE,
  token TEXT UNIQUE DEFAULT uuid_generate_v4()
);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_profiles_modtime
BEFORE UPDATE ON profiles
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_affirmations_modtime
BEFORE UPDATE ON affirmations
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_scheduled_calls_modtime
BEFORE UPDATE ON scheduled_calls
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_call_history_modtime
BEFORE UPDATE ON call_history
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_organizations_modtime
BEFORE UPDATE ON organizations
FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- Set up Row Level Security (RLS) policies
-- Enable RLS on all tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE affirmations ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE transcriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_invitations ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view their own profile"
ON profiles FOR SELECT
USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
ON profiles FOR UPDATE
USING (auth.uid() = id);

CREATE POLICY "Users can insert their own profile"
ON profiles FOR INSERT
WITH CHECK (auth.uid() = id);

-- Affirmations policies
CREATE POLICY "Anyone can view public affirmations"
ON affirmations FOR SELECT
USING (is_public = true);

CREATE POLICY "Users can view their own affirmations"
ON affirmations FOR SELECT
USING (auth.uid() = created_by);

CREATE POLICY "Users can insert their own affirmations"
ON affirmations FOR INSERT
WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Users can update their own affirmations"
ON affirmations FOR UPDATE
USING (auth.uid() = created_by);

CREATE POLICY "Users can delete their own affirmations"
ON affirmations FOR DELETE
USING (auth.uid() = created_by);

-- Organization members can view organization affirmations
CREATE POLICY "Organization members can view organization affirmations"
ON affirmations FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM organization_members om
    JOIN affirmations a ON a.created_by = om.user_id
    WHERE om.user_id = auth.uid()
    AND om.organization_id = (
      SELECT organization_id FROM organization_members WHERE user_id = created_by LIMIT 1
    )
  )
);

-- Scheduled calls policies
CREATE POLICY "Users can view their own scheduled calls"
ON scheduled_calls FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own scheduled calls"
ON scheduled_calls FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own scheduled calls"
ON scheduled_calls FOR UPDATE
USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own scheduled calls"
ON scheduled_calls FOR DELETE
USING (auth.uid() = user_id);

-- Call history policies
CREATE POLICY "Users can view their own call history"
ON call_history FOR SELECT
USING (auth.uid() = user_id);

-- Transcriptions policies
CREATE POLICY "Users can view transcriptions for their own calls"
ON transcriptions FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM call_history
    WHERE id = call_id AND user_id = auth.uid()
  )
);

-- Organizations policies
CREATE POLICY "Organization owners and admins can view their organizations"
ON organizations FOR SELECT
USING (
  auth.uid() = owner_id OR
  EXISTS (
    SELECT 1 FROM organization_members
    WHERE organization_id = id AND user_id = auth.uid() AND role IN ('owner', 'admin')
  )
);

CREATE POLICY "Users can create organizations"
ON organizations FOR INSERT
WITH CHECK (auth.uid() = owner_id);

CREATE POLICY "Organization owners can update their organizations"
ON organizations FOR UPDATE
USING (auth.uid() = owner_id);

CREATE POLICY "Organization owners can delete their organizations"
ON organizations FOR DELETE
USING (auth.uid() = owner_id);

-- Organization members policies
CREATE POLICY "Organization members can view memberships"
ON organization_members FOR SELECT
USING (
  auth.uid() = user_id OR
  EXISTS (
    SELECT 1 FROM organization_members
    WHERE organization_id = organization_members.organization_id 
    AND user_id = auth.uid() 
    AND role IN ('owner', 'admin')
  )
);

CREATE POLICY "Organization owners and admins can manage members"
ON organization_members FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1 FROM organization_members
    WHERE organization_id = organization_members.organization_id 
    AND user_id = auth.uid() 
    AND role IN ('owner', 'admin')
  )
);

CREATE POLICY "Organization owners and admins can update members"
ON organization_members FOR UPDATE
USING (
  EXISTS (
    SELECT 1 FROM organization_members
    WHERE organization_id = organization_members.organization_id 
    AND user_id = auth.uid() 
    AND role IN ('owner', 'admin')
  )
);

CREATE POLICY "Organization owners and admins can remove members"
ON organization_members FOR DELETE
USING (
  EXISTS (
    SELECT 1 FROM organization_members
    WHERE organization_id = organization_members.organization_id 
    AND user_id = auth.uid() 
    AND role IN ('owner', 'admin')
  )
);

-- Organization invitations policies
CREATE POLICY "Organization owners and admins can view invitations"
ON organization_invitations FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM organization_members
    WHERE organization_id = organization_invitations.organization_id 
    AND user_id = auth.uid() 
    AND role IN ('owner', 'admin')
  )
);

CREATE POLICY "Organization owners and admins can create invitations"
ON organization_invitations FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1 FROM organization_members
    WHERE organization_id = organization_invitations.organization_id 
    AND user_id = auth.uid() 
    AND role IN ('owner', 'admin')
  )
);

-- Create default affirmations
INSERT INTO affirmations (text, category, is_custom, is_public)
VALUES
  ('I am capable of achieving my goals and dreams.', 'confidence', false, true),
  ('I embrace the day with positivity and purpose.', 'morning', false, true),
  ('I trust my intuition and make wise decisions.', 'wisdom', false, true),
  ('I am grateful for the abundance in my life.', 'gratitude', false, true),
  ('I radiate confidence, energy, and positivity.', 'confidence', false, true),
  ('Today I choose joy and gratitude.', 'gratitude', false, true),
  ('I am worthy of success and happiness.', 'confidence', false, true),
  ('I transform challenges into opportunities for growth.', 'growth', false, true),
  ('My potential is limitless, and I can achieve anything.', 'confidence', false, true),
  ('I am becoming the best version of myself each day.', 'growth', false, true),
  ('I approach each day with courage and determination.', 'courage', false, true),
  ('My mind is clear, focused, and ready for the day ahead.', 'morning', false, true),
  ('I am in control of my thoughts and emotions.', 'mindfulness', false, true),
  ('I release all negativity and embrace positivity.', 'mindfulness', false, true),
  ('I am surrounded by love and support.', 'relationships', false, true)
ON CONFLICT DO NOTHING;

-- Create a function to handle new user registration
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO profiles (id, first_name, last_name, phone_number)
  VALUES (
    NEW.id,
    NEW.raw_user_meta_data->>'first_name',
    NEW.raw_user_meta_data->>'last_name',
    NEW.raw_user_meta_data->>'phone_number'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger the function every time a user is created
CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();
