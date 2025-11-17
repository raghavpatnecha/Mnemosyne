/**
 * Shared types used across multiple resources
 */

/**
 * Pagination options using page and page_size
 * (Used by collections)
 */
export interface PaginationOptions {
  /** Page number (1-indexed) */
  page?: number;
  /** Number of items per page */
  page_size?: number;
}

/**
 * Pagination options using limit and offset
 * (Used by documents and chat)
 */
export interface LimitOffsetPagination {
  /** Maximum number of items to return */
  limit?: number;
  /** Number of items to skip */
  offset?: number;
}

/**
 * Flexible metadata dictionary for arbitrary key-value pairs
 */
export interface Metadata {
  [key: string]: unknown;
}

/**
 * Standard list response with pagination info
 */
export interface PaginatedResponse<T> {
  /** Array of items */
  data: T[];
  /** Total number of items (across all pages) */
  total: number;
  /** Current page number */
  page: number;
  /** Items per page */
  page_size: number;
}

/**
 * ISO 8601 timestamp string
 * @example "2024-01-15T10:00:00Z"
 */
export type Timestamp = string;

/**
 * UUID v4 string
 * @example "550e8400-e29b-41d4-a716-446655440000"
 */
export type UUID = string;
