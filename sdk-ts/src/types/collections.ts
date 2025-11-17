/**
 * Type definitions for Collections API
 */

import { Pagination } from './common.js';

/**
 * Schema for creating a new collection
 */
export interface CollectionCreate {
  name: string;
  description?: string;
  metadata?: Record<string, unknown>;
  config?: Record<string, unknown>;
}

/**
 * Schema for updating a collection (all fields optional)
 */
export interface CollectionUpdate {
  name?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  config?: Record<string, unknown>;
}

/**
 * Schema for collection responses
 */
export interface CollectionResponse {
  id: string;
  user_id: string;
  name: string;
  description?: string;
  metadata: Record<string, unknown>;
  config: Record<string, unknown>;
  document_count: number;
  created_at: string;
  updated_at?: string;
}

/**
 * Schema for paginated list of collections
 */
export interface CollectionListResponse {
  data: CollectionResponse[];
  pagination: Pagination;
}
