-- ==================================================
-- Supabase Schema for Agri-AI (VANYA)
-- Run this in your Supabase SQL Editor
-- ==================================================

-- 1. PROFILES TABLE (Linked to auth.users)
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  full_name text,
  phone text,
  avatar_url text,
  role text default 'farmer' check (role in ('farmer', 'admin', 'expert')),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Enable RLS on profiles
alter table public.profiles enable row level security;

-- Drop existing policies if any
drop policy if exists "Users can view their own profile" on public.profiles;
drop policy if exists "Users can update their own profile" on public.profiles;
drop policy if exists "Users can insert their own profile" on public.profiles;
drop policy if exists "Service role full access to profiles" on public.profiles;

-- RLS Policies: users read/update only their own row
create policy "Users can view their own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update their own profile"
  on public.profiles for update
  using (auth.uid() = id);

create policy "Users can insert their own profile"
  on public.profiles for insert
  with check (auth.uid() = id);

-- Trigger to automatically create a profile row on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email, full_name, role)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
    'farmer'
  )
  on conflict (id) do nothing;
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();


-- 2. PLANTS TABLE (Plant tracking across visits)
create table if not exists public.plants (
  id text primary key,
  farmer_id text not null,
  plant_name text,
  crop text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.plants enable row level security;

create policy "Farmers can view their own plants"
  on public.plants for select
  using (auth.uid()::text = farmer_id);

create policy "Farmers can manage their own plants"
  on public.plants for all
  using (auth.uid()::text = farmer_id);


-- 3. PREDICTIONS TABLE
create table if not exists public.predictions (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  farmer_id text,
  plant_id text,
  label text,
  confidence float,
  severity_pct float,
  severity_level text,
  trend text,
  risk_now text,
  lat float,
  lon float,
  image_thumb text,
  report jsonb,
  needs_review boolean default false,
  status text default 'pending',   -- pending | confirmed | corrected | rejected
  expert_label text,
  expert_notes text,
  verified_at timestamptz,
  is_synthetic boolean default false
);

alter table public.predictions enable row level security;

create policy "Farmers can view their own predictions"
  on public.predictions for select
  using (auth.uid()::text = farmer_id);


-- 4. VERIFICATIONS TABLE
create table if not exists public.verifications (
  id uuid primary key default gen_random_uuid(),
  prediction_id uuid references public.predictions(id),
  decision text,
  original_label text,
  expert_label text,
  notes text,
  created_at timestamptz default now()
);

alter table public.verifications enable row level security;


-- 5. AVATARS STORAGE BUCKET
insert into storage.buckets (id, name, public)
values ('avatars', 'avatars', true)
on conflict (id) do nothing;

-- Storage policies for avatars
create policy "Avatar images are publicly accessible"
  on storage.objects for select
  using (bucket_id = 'avatars');

create policy "Authenticated users can upload avatar"
  on storage.objects for insert
  with check (bucket_id = 'avatars' and auth.role() = 'authenticated');

create policy "Users can update their own avatar"
  on storage.objects for update
  using (bucket_id = 'avatars' and auth.uid()::text = (storage.foldername(name))[1]);


-- ==================================================
-- HELPER SQL FOR ADMIN PROMOTION
-- To make any account an admin, run:
-- update public.profiles set role = 'admin' where email = 'YOUR_EMAIL@example.com';
-- ==================================================
