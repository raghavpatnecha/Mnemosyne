/**
 * Common types shared across the SDK
 */

/**
 * Pagination information for list responses
 */
export interface Pagination {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

/**
 * Generic list response with pagination
 */
export interface PaginatedResponse<T> {
  data: T[];
  pagination: Pagination;
}
