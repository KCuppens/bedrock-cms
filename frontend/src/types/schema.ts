/**
 * TypeScript interfaces for Schema.org structured data
 */

export type SchemaType =
  | 'Article'
  | 'BlogPosting'
  | 'WebPage'
  | 'Organization'
  | 'BreadcrumbList'
  | 'Person'
  | 'Product'
  | 'Event'
  | 'FAQPage'
  | 'HowTo'
  | 'LocalBusiness';

export interface SchemaObject {
  id: string;
  type: SchemaType;
  auto_generated: boolean;
  data: Record<string, any>;
}

export interface SchemaValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface SchemaTemplate {
  type: string;
  template: Record<string, any>;
}

export interface SchemaTypeSpec {
  type: string;
  required_properties: string[];
  recommended_properties: string[];
}

// Base Schema.org types

export interface BaseSchema {
  '@context'?: string;
  '@type': string;
  [key: string]: any;
}

export interface ArticleSchema extends BaseSchema {
  '@type': 'Article';
  headline: string;
  description?: string;
  image?: string | string[];
  author?: PersonSchema | OrganizationSchema;
  publisher?: OrganizationSchema;
  datePublished?: string;
  dateModified?: string;
}

export interface BlogPostingSchema extends ArticleSchema {
  '@type': 'BlogPosting';
  articleSection?: string;
  wordCount?: number;
}

export interface WebPageSchema extends BaseSchema {
  '@type': 'WebPage';
  name: string;
  description?: string;
  url?: string;
  datePublished?: string;
  dateModified?: string;
  image?: string | string[];
  breadcrumb?: BreadcrumbListSchema;
}

export interface OrganizationSchema extends BaseSchema {
  '@type': 'Organization';
  name: string;
  url?: string;
  logo?: ImageObjectSchema | string;
  contactPoint?: ContactPointSchema;
  sameAs?: string[];
}

export interface PersonSchema extends BaseSchema {
  '@type': 'Person';
  name: string;
  email?: string;
  url?: string;
  image?: string;
}

export interface ImageObjectSchema extends BaseSchema {
  '@type': 'ImageObject';
  url: string;
  width?: number;
  height?: number;
}

export interface BreadcrumbListSchema extends BaseSchema {
  '@type': 'BreadcrumbList';
  itemListElement: ListItemSchema[];
}

export interface ListItemSchema extends BaseSchema {
  '@type': 'ListItem';
  position: number;
  name: string;
  item?: string;
}

export interface FAQPageSchema extends BaseSchema {
  '@type': 'FAQPage';
  mainEntity: QuestionSchema[];
}

export interface QuestionSchema extends BaseSchema {
  '@type': 'Question';
  name: string;
  acceptedAnswer: AnswerSchema;
}

export interface AnswerSchema extends BaseSchema {
  '@type': 'Answer';
  text: string;
}

export interface HowToSchema extends BaseSchema {
  '@type': 'HowTo';
  name: string;
  description?: string;
  image?: string | string[];
  totalTime?: string;
  step: HowToStepSchema[];
}

export interface HowToStepSchema extends BaseSchema {
  '@type': 'HowToStep';
  name: string;
  text: string;
  image?: string;
}

export interface ContactPointSchema extends BaseSchema {
  '@type': 'ContactPoint';
  telephone: string;
  contactType: string;
  email?: string;
  availableLanguage?: string | string[];
}

export interface EventSchema extends BaseSchema {
  '@type': 'Event';
  name: string;
  startDate: string;
  endDate?: string;
  location?: PlaceSchema;
  description?: string;
  image?: string | string[];
  organizer?: OrganizationSchema | PersonSchema;
}

export interface PlaceSchema extends BaseSchema {
  '@type': 'Place';
  name: string;
  address?: string | PostalAddressSchema;
}

export interface PostalAddressSchema extends BaseSchema {
  '@type': 'PostalAddress';
  streetAddress?: string;
  addressLocality?: string;
  addressRegion?: string;
  postalCode?: string;
  addressCountry?: string;
}
