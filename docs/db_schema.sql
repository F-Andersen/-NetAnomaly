--
-- PostgreSQL database dump
--

-- Dumped from database version 16.8
-- Dumped by pg_dump version 16.8

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: experiment_metrics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.experiment_metrics (
    run_id character varying(128) NOT NULL,
    model character varying(64) NOT NULL,
    data_mode character varying(16) NOT NULL,
    n bigint NOT NULL,
    n_attack bigint NOT NULL,
    n_benign bigint NOT NULL,
    tp bigint NOT NULL,
    fp bigint NOT NULL,
    tn bigint NOT NULL,
    fn bigint NOT NULL,
    accuracy double precision NOT NULL,
    "precision" double precision NOT NULL,
    recall double precision NOT NULL,
    f1 double precision NOT NULL,
    fpr double precision NOT NULL,
    pr_auc double precision NOT NULL,
    roc_auc double precision NOT NULL,
    threshold double precision NOT NULL,
    score_seconds double precision NOT NULL,
    microseconds_per_record double precision NOT NULL
);


--
-- Name: experiment_per_attack; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.experiment_per_attack (
    run_id character varying(128) NOT NULL,
    model character varying(64) NOT NULL,
    label character varying(64) NOT NULL,
    n bigint NOT NULL,
    flagged bigint NOT NULL,
    flagged_share double precision NOT NULL
);


--
-- Name: flow_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.flow_events (
    id bigint NOT NULL,
    event_time timestamp with time zone NOT NULL,
    received_at timestamp with time zone NOT NULL,
    source character varying(32) NOT NULL,
    src_ip character varying(64),
    src_port integer,
    dst_ip character varying(64),
    dst_port integer,
    true_label character varying(64),
    features jsonb NOT NULL
);


--
-- Name: flow_events_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.flow_events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: flow_events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.flow_events_id_seq OWNED BY public.flow_events.id;


--
-- Name: model_versions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.model_versions (
    version character varying(128) NOT NULL,
    algorithm character varying(64) NOT NULL,
    run_id character varying(128) NOT NULL,
    data_mode character varying(16) NOT NULL,
    threshold double precision NOT NULL,
    seed integer NOT NULL,
    params jsonb NOT NULL,
    registered_at timestamp with time zone NOT NULL
);


--
-- Name: predictions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.predictions (
    id bigint NOT NULL,
    event_id bigint NOT NULL,
    model_version character varying(128) NOT NULL,
    score double precision NOT NULL,
    threshold double precision NOT NULL,
    is_anomaly boolean NOT NULL,
    event_time timestamp with time zone NOT NULL,
    decided_at timestamp with time zone NOT NULL
);


--
-- Name: predictions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.predictions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: predictions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.predictions_id_seq OWNED BY public.predictions.id;


--
-- Name: flow_events id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.flow_events ALTER COLUMN id SET DEFAULT nextval('public.flow_events_id_seq'::regclass);


--
-- Name: predictions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.predictions ALTER COLUMN id SET DEFAULT nextval('public.predictions_id_seq'::regclass);


--
-- Name: experiment_metrics experiment_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experiment_metrics
    ADD CONSTRAINT experiment_metrics_pkey PRIMARY KEY (run_id, model);


--
-- Name: experiment_per_attack experiment_per_attack_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.experiment_per_attack
    ADD CONSTRAINT experiment_per_attack_pkey PRIMARY KEY (run_id, model, label);


--
-- Name: flow_events flow_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.flow_events
    ADD CONSTRAINT flow_events_pkey PRIMARY KEY (id);


--
-- Name: model_versions model_versions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.model_versions
    ADD CONSTRAINT model_versions_pkey PRIMARY KEY (version);


--
-- Name: predictions predictions_event_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_event_id_key UNIQUE (event_id);


--
-- Name: predictions predictions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_pkey PRIMARY KEY (id);


--
-- Name: ix_flow_events_event_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_flow_events_event_time ON public.flow_events USING btree (event_time);


--
-- Name: ix_predictions_anomaly; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_predictions_anomaly ON public.predictions USING btree (is_anomaly, id);


--
-- Name: ix_predictions_event_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_predictions_event_time ON public.predictions USING btree (event_time);


--
-- Name: predictions predictions_event_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_event_id_fkey FOREIGN KEY (event_id) REFERENCES public.flow_events(id) ON DELETE CASCADE;


--
-- Name: predictions predictions_model_version_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.predictions
    ADD CONSTRAINT predictions_model_version_fkey FOREIGN KEY (model_version) REFERENCES public.model_versions(version);


--
-- PostgreSQL database dump complete
--
